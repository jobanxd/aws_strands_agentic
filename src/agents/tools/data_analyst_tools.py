"""
Tools under the Data Analyst Agent
"""

import json
import asyncio

from strands import tool
from typing import List

from src.agents.state import PipelineState
from src.models.agent_models import (
    DataAnalystOutput,
    ServiceLinkBundle,
)
from src.utils.exceptions import InsufficientDataError
from src.utils.logger import logger


def make_tool(state: PipelineState) -> list:
    """
    Returns all Data Analyst Agent tools bount to given pipeline state
    """

    @tool
    def extract_party_id(party_id: str) -> str:
        """
        Extracts party_id.
        """

        # Store in state
        state.party_id = party_id
        state.mark_step("extract_party_id")

        logger.info(f"Party ID extracted: {state.party_id}")
        return json.dumps(
            {
                "party_id": state.party_id,
                "status": "ok"
            }
        )
    
    @tool
    def fetch_kyc_data(party_id: str) -> str:
        """
        Fetch KYCnet drilldown and review data for given party_id
        """
        async def _fetch():
            kyc_party_info = await state.db.kyc.get_party_info(party_id)
            logger.info(
                f"Query Output:\n{json.dumps([item.model_dump() for item in kyc_party_info], indent=4, default=str)}"
            )

            if len(kyc_party_info) < 2:
                raise InsufficientDataError(
                    f"Party ID {party_id} has fewer than 2 reviews. "
                    "A ground truth review and at least one review to process are required."
                )
            
            latest = kyc_party_info[1]

            # Extract the review data of the latest review ID
            review_info = await state.db.kyc.get_review_info(latest.review_id)

            # Store in state
            state.kyc_party_info = kyc_party_info
            state.latest_kyc_party_info = latest
            state.review_info = review_info
            state.mark_step("fetch_kyc_data")

            logger.info(f"KYC Data fetched for party: {party_id}")
            return {
                "party_id": party_id,
                "review_id": latest.review_id,
                "party_name": latest.party_name,
                "last_automated_risk": latest.last_automated_risk,
                "review_count": len(kyc_party_info),
                "status": "ok",
            }

        try:
            return json.dumps(asyncio.run(_fetch()))
        except InsufficientDataError:
            raise
        except Exception as exc:
            logger.error(f"fetch_kyc_data failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def fetch_svoc_data(party_id: str) -> str:
        """
        Fetch SVOC data for given party_id
        """
        async def _fetch():
            if not state.latest_kyc_party_info:
                return {"error": "KYC data not loaded. Run fetch_kyc_data first.", "status": "failed"}

            svoc_data = await state.db.kyc.get_svoc_extract(
                state.latest_kyc_party_info.entrp_party_ident
            )
            logger.info(
                f"Query Output:\n{json.dumps([item.model_dump() for item in svoc_data], indent=4, default=str)}"
            )

            if not svoc_data:
                return {
                    "error": f"SVoC data not found for party: {state.latest_kyc_party_info.party_name}",
                    "status": "failed",
                }

            # Store in state
            state.svoc_data = svoc_data
            state.mark_step("fetch_svoc_data")

            logger.info(
                f"SVoC data fetched: {len(svoc_data)} accounts for party: {party_id}"
            )
            return {
                "party_id": party_id,
                "total_accounts": len(svoc_data),
                "accounts": [
                    {"agmt_id": s.agmt_id, "account_no": s.account_no, "closed": s.closed}
                    for s in svoc_data
                ],
                "status": "ok",
            }

        try:
            return json.dumps(asyncio.run(_fetch()))
        except Exception as exc:
            logger.error(f"fetch_svoc_data failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def fetch_servicelink_data(party_id: str) -> str:
        """
        Fetch ServiceLink transaction bundles for each SVoC account.
        """
        async def _fetch():
            if not state.svoc_data:
                return {"error": "SVoC data not loaded. Run fetch_svoc_data first.", "status": "failed"}

            bundles:List[ServiceLinkBundle] = []

            for svoc_record in state.svoc_data:
                logger.info(f"Extracting ServiceLink data for AGMT ID: {svoc_record.agmt_id}")
                bundle = await state.db.servicelink.get_servicelink_bundle(svoc_record.agmt_id)
                if bundle:
                    bundles.append(bundle)
                    logger.info(
                        f"ServiceLink bundle fetched for agmt_id: {svoc_record.agmt_id}"
                    )
                    logger.info(
                        f"ServiceLink Bundle: {json.dumps(bundle.model_dump(), indent=4, default=str)}"
                    )

            # Store in state
            state.servicelink_bundles = bundles
            state.mark_step("fetch_servicelink_data")

            return {
                "party_id": party_id,
                "bundles_fetched": len(bundles),
                "accounts": [b.account_details.agmt_id for b in bundles],
                "status": "ok",
            }

        try:
            return json.dumps(asyncio.run(_fetch()))
        except Exception as exc:
            logger.error(f"fetch_servicelink_data failed:{exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def check_account_status(party_id: str) -> str:
        """
        Check whether the party has at least one open/active account.
        If ALL accounts are closed, returns an error and the pipeline stops —
        the review status is marked as 'Not Applicable'.
        Must be called after fetch_svoc_data.
        """
        async def _check():
            if not state.svoc_data:
                return {"error": "SVoC data not loaded. Run fetch_svoc_data first.", "status": "failed"}

            closed = [s for s in state.svoc_data if (s.closed or "N").upper() == "Y"]
            open_accounts = [s for s in state.svoc_data if (s.closed or "N").upper() != "Y"]

            has_active = len(open_accounts) > 0

            if not has_active:
                # Mark as Not Applicable in sharepoint
                if state.review_info:
                    await state.db.sharepoint.update_review_status(
                        party_id=party_id,
                        review_id=state.review_info.review_id,
                        status="Not Applicable",
                    )
                logger.warning(f"All accounts closed for party: {party_id}")
                return {
                    "has_active_account": False,
                    "open_count": 0,
                    "closed_count": len(closed),
                    "closed_accounts": [
                        {"account_no": s.account_no, "nsc": s.nsc} for s in closed
                    ],
                    "status": "not_applicable",
                    "message": "All accounts are closed. Review marked as Not Applicable.",
                }

            # Store in state
            state.mark_step("check_account_status")
            logger.info(
                f"Account status OK: {len(open_accounts)} open, {len(closed)} closed"
            )

            return {
                "has_active_account": True,
                "open_count": len(open_accounts),
                "closed_count": len(closed),
                "status": "ok",
            }

        try:
            return json.dumps(asyncio.run(_check()))
        except Exception as exc:
            logger.error(f"check_account_status failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def extract_documents(party_id: str) -> str:
        """
        Extract and analyze identity and employment documents for the party
        using the document extraction service (replaces AWS Textract).
        Must be called after fetch_kyc_data.
        Returns document analysis including proof of ID and employment details.
        """
        async def _extract():
            if not state.latest_kyc_party_info:
                return {"error": "KYC data not loaded. Run fetch_kyc_data first.", "status": "failed"}

            textract_data = await state.db.textract.extract_party_documents(
                party_id=party_id,
                review_id=state.latest_kyc_party_info.review_id,
                db=state.db,
            )

            state.textract_data = textract_data
            state.mark_step("extract_documents")

            if not textract_data:
                logger.warning(f"No documents found for party: {party_id}")
                return {"party_id": party_id, "documents_found": False, "status": "ok"}

            result = {
                "party_id": party_id,
                "documents_found": True,
                "status": "ok",
            }

            if textract_data.proof_of_id:
                result["proof_of_id"] = {
                    "document_type": textract_data.proof_of_id.document_type,
                    "name": textract_data.proof_of_id.name,
                    "dob": textract_data.proof_of_id.dob,
                    "country_of_birth": textract_data.proof_of_id.country_of_birth,
                    "country_of_citizenship": textract_data.proof_of_id.country_of_citizenship,
                }

            if textract_data.employment:
                result["employment"] = {
                    "employment_status": textract_data.employment.employment_status,
                    "employer": textract_data.employment.employer,
                }

            logger.info(f"Documents extracted for party: {party_id}")
            return result

        try:
            return json.dumps(asyncio.run(_extract()))
        except Exception as exc:
            logger.error(f"extract_documents failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def extract_previous_residence(party_id: str) -> str:
        """
        Check if a previous length of residence record is needed and retrieve it.
        Only applies when: country of citizenship is high-risk AND country of residence is Ireland.
        Must be called after extract_documents and fetch_kyc_data.
        Returns the previous length of residence value, or null if not applicable.
        """
        async def _extract():
            if not state.review_info or not state.kyc_party_info:
                return {
                    "error": "KYC and review data not loaded. Run fetch_kyc_data first.",
                    "status": "failed"
                }

            # Determine country of citizenship — prefer textract, fall back to review_info
            country_of_citizenship = None
            if state.textract_data and state.textract_data.proof_of_id:
                country_of_citizenship = state.textract_data.proof_of_id.country_of_citizenship
            if not country_of_citizenship:
                country_of_citizenship = state.review_info.country_of_citizenship

            if not country_of_citizenship:
                logger.info("No country_of_citizenship found — skipping residence check")
                state.mark_step("extract_previous_residence")
                return {"previous_length_of_residence": None, "reason": "No citizenship country found", "status": "ok"}

            # Check if high-risk country
            is_high_risk = await state.db.country_risk.is_high_risk_country(country_of_citizenship)
            if not is_high_risk:
                logger.info(
                    f"{country_of_citizenship} is not high-risk — length of residence not required",
                )
                state.mark_step("extract_previous_residence")
                return {
                    "previous_length_of_residence": None,
                    "reason": f"{country_of_citizenship} is not a high-risk country",
                    "status": "ok"
                }

            # Check Ireland condition
            country_of_residence = state.review_info.country_of_residence
            needs_residence = (
                country_of_residence and
                country_of_residence.lower() == "ireland"
            )

            if not needs_residence:
                state.mark_step("extract_previous_residence")
                return {
                    "previous_length_of_residence": None,
                    "reason": "Residence conditions not met (not Ireland)",
                    "status": "ok"
                }

            # Look for the previous review's length of residence
            sorted_info = sorted(
                state.kyc_party_info,
                key=lambda x: x.date_current_review_started,
                reverse=True
            )
            # [0] = ground truth, [1] = current, [2] = previous (if exists)
            if len(sorted_info) > 2:
                prev_review = await state.db.kyc.get_review_info(sorted_info[2].review_id)
                prev_lor = prev_review.length_of_residence if prev_review else None
            else:
                prev_lor = "No previous length of residence recorded. Length of Residence still required."

            state.previous_length_of_residence = prev_lor
            state.mark_step("extract_previous_residence")
            logger.info(f"Previous length of residence: {prev_lor}")

            return {
                "previous_length_of_residence": prev_lor,
                "country_of_citizenship": country_of_citizenship,
                "country_of_residence": country_of_residence,
                "status": "ok",
            }

        try:
            return json.dumps(asyncio.run(_extract()))
        except Exception as exc:
            logger.error(f"extract_previous_residence failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})

    @tool
    def save_analyst_output(party_id: str) -> str:
        """
        Consolidate all extracted data into a DataAnalystOutput and save it to state.
        Call this as the final step after all extraction tools have run.
        Returns a summary of everything extracted during this agent run.
        """
        if not state.latest_kyc_party_info:
            return json.dumps({"error": "Cannot save: KYC data not loaded", "status": "failed"})

        # Build structured output
        output = DataAnalystOutput(
            party_id=state.party_id,
            review_info=state.review_info,
            textract_data=state.textract_data,
            svoc_data=state.svoc_data or [],
            servicelink_bundles=state.servicelink_bundles or [],
            previous_length_of_residence=state.previous_length_of_residence,
            summary=_build_summary(state),
        )

        state.data_analyst_output = output
        state.mark_step("save_analyst_output")

        logger.info(f"Output saved for party: {party_id}")
        return json.dumps({
            "status": "success",
            "party_id": party_id,
            "steps_completed": state.steps_completed,
            "summary": output.summary,
        })

    return [
        extract_party_id,
        fetch_kyc_data,
        fetch_svoc_data,
        fetch_servicelink_data,
        check_account_status,
        extract_previous_residence,
        save_analyst_output,
    ]


# Internal helpers (not tools — not exposed to the agent)
def _build_summary(state: PipelineState) -> str:
    """Build the human-readable summary from state. Mirrors create_summary() from original."""
    p = state.latest_kyc_party_info
    r = state.review_info
    t = state.textract_data
    bundles = state.servicelink_bundles or []
    svoc = state.svoc_data or []

    # Proof of ID
    pid = t.proof_of_id if t else None
    emp = t.employment if t else None

    accounts_str = ", ".join(b.account_details.agmt_id for b in bundles[:3])
    if len(bundles) > 3:
        accounts_str += "..."

    return f"""
Data Analyst Extraction Summary for {p.party_name if p else 'Unknown'} (Party ID: {state.party_id})

KYCnet Data Extracted
  - Party ID: {state.party_id}
  - Latest Review ID: {p.review_id if p else 'N/A'}
  - Last Automated Risk: {p.last_automated_risk if p else 'N/A'}

Identity Document Analysis
  - Document Type: {pid.document_type if pid else 'N/A'}
  - Name: {pid.name if pid else 'N/A'}
  - DOB: {pid.dob if pid else 'N/A'}
  - Country of Birth: {pid.country_of_birth if pid else 'N/A'}

Employment Information
  - Employment Status: {emp.employment_status if emp else 'N/A'}
  - Employer: {emp.employer if emp else 'N/A'}

SVoC Data Extracted
  - Total Accounts Found: {len(svoc)}

ServiceLink Data Extracted
  - Total Bundles: {len(bundles)}
  - Accounts Processed: {accounts_str or 'None'}

Previous Length of Residence: {state.previous_length_of_residence or 'N/A'}

Steps Completed: {', '.join(state.steps_completed)}
Data extraction completed successfully.
""".strip()
