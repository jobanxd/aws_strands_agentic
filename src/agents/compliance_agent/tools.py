# src/agents/compliance_agent/tools.py

import json
import asyncio

from strands import Agent
from strands import tool

from src.core.model_factory import get_model
from src.workflows.state import PipelineState
from src.models.agent_models import (
    IdentificationValidationResults,
    EmploymentValidationResults,
    AddressValidationResults,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)
AGENT_NAME = "Compliance Agent"


def make_tools(state: PipelineState) -> list:

    @tool
    def run_document_validations(party_id: str) -> str:
        """
        Run identification, employment, and proof of address validations
        against KYCnet review info and activity monitor results.
        Each validation is an internal LLM agent call.
        Saves results directly to state.
        Must be called first.
        """
        async def _validate():
            if not state.data_analyst_summary:
                return {"error": "DataAnalystOutput not in state.", "status": "failed"}
            if not state.activity_monitor_summary:
                return {"error": "ActivityMonitorOutput not in state.", "status": "failed"}

            if not state.textract_data:
                return {"error": "No textract data found in DataAnalystOutput.", "status": "failed"}

            identification_validation = None
            employment_validation = None
            proof_of_address_validation = None

            # ── Identification ────────────────────────────────────────────────
            if state.textract_data.proof_of_id is not None:
                logger.info(f"[{AGENT_NAME}] Validating identification document")
                prompt_template = await state.db.agent.get_agent_prompt(8.0)
                if not prompt_template:
                    return {"error": "Identification validation prompt (8.0) not found.", "status": "failed"}

                textract_dict = state.textract_data.model_dump()
                if isinstance(textract_dict.get("proof_of_id"), dict):
                    textract_dict["proof_of_id"].pop("document_path", None)

                prompt = prompt_template.format(
                    proof_of_id_data=json.dumps(textract_dict.get("proof_of_id"), indent=2, default=str),
                    review_info_data=json.dumps(state.review_info.model_dump(), indent=2, default=str),
                )

                agent = Agent(
                    system_prompt="""You are a compliance document validator.
                    Analyze the provided data and return ONLY a valid JSON object.
                    No explanation. No markdown. No code blocks. Raw JSON only.""",
                    model=get_model(),
                )
                try:
                    response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                    result = json.loads(response)
                    identification_validation = IdentificationValidationResults(**result)
                    logger.info(f"[{AGENT_NAME}] Identification validation: matches={identification_validation.overall_matches}")
                except Exception as exc:
                    logger.error(f"[{AGENT_NAME}] Identification validation failed: {exc}")
                    identification_validation = IdentificationValidationResults(
                        overall_matches=False,
                        document_type="unknown",
                        is_full_name_matching=False,
                        is_dob_matching=None,
                        is_gender_matching=None,
                        is_country_of_birth_matching=None,
                        is_country_of_citizenship_matching=None,
                        analysis=f"Validation error: {exc}",
                        summary=f"Identification validation failed: {exc}",
                        reason_for_unmatch="Unexpected error during validation.",
                        recommendation_for_unmatch="Re-run or contact support.",
                    )

            # ── Employment ────────────────────────────────────────────────────
            if state.textract_data.employment is not None:
                logger.info(f"[{AGENT_NAME}] Validating employment document")
                prompt_template = await state.db.agent.get_agent_prompt(9.0)
                if not prompt_template:
                    return {"error": "Employment validation prompt (9.0) not found.", "status": "failed"}

                textract_dict = state.textract_data.model_dump()
                if isinstance(textract_dict.get("employment"), dict):
                    textract_dict["employment"].pop("document_path", None)

                prompt = prompt_template.format(
                    employment_doc_data=json.dumps(textract_dict.get("employment"), indent=2, default=str),
                    review_info_data=json.dumps(state.review_info.model_dump(), indent=2, default=str),
                    employment_results_data=json.dumps(state.employment_analysis_results, indent=2, default=str),
                )

                agent = Agent(
                    system_prompt="""You are a compliance document validator.
                    Analyze the provided data and return ONLY a valid JSON object.
                    No explanation. No markdown. No code blocks. Raw JSON only.""",
                    model=get_model(),
                )
                try:
                    response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                    result = json.loads(response)
                    employment_validation = EmploymentValidationResults(**result)
                    logger.info(f"[{AGENT_NAME}] Employment validation: matches={employment_validation.overall_matches}")
                except Exception as exc:
                    logger.error(f"[{AGENT_NAME}] Employment validation failed: {exc}")
                    employment_validation = EmploymentValidationResults(
                        overall_matches=False,
                        document_type="unknown",
                        is_full_name_matching=False,
                        is_employment_status_matching=False,
                        is_employer_matching=False,
                        analysis=f"Validation error: {exc}",
                        summary=f"Employment validation failed: {exc}",
                        reason_for_unmatch="Unexpected error during validation.",
                        recommendation_for_unmatch="Re-run or contact support.",
                    )

            # ── Proof of Address ──────────────────────────────────────────────
            if state.textract_data.proof_of_address is not None:
                logger.info(f"[{AGENT_NAME}] Validating proof of address")
                prompt_template = await state.db.agent.get_agent_prompt(10.0)
                if not prompt_template:
                    return {"error": "Proof of address prompt (10.0) not found.", "status": "failed"}

                textract_dict = state.textract_data.model_dump()
                if isinstance(textract_dict.get("proof_of_address"), dict):
                    textract_dict["proof_of_address"].pop("document_path", None)
                    textract_dict["proof_of_address"] = {
                        k: v for k, v in textract_dict["proof_of_address"].items() if v is not None
                    }

                addresses = []
                for bundle in (state.servicelink_bundles or []):
                    if bundle.account_details and bundle.account_details.account_address:
                        addresses.append({
                            "agmt_id": bundle.account_details.agmt_id,
                            "account_address": bundle.account_details.account_address,
                        })

                prompt = prompt_template.format(
                    proof_of_address_data=json.dumps(textract_dict.get("proof_of_address"), indent=2, default=str),
                    review_info_data=json.dumps(state.review_info.model_dump(), indent=2, default=str),
                    servicelink_addresses=json.dumps(addresses, indent=2, default=str),
                )

                agent = Agent(
                    system_prompt="""You are a compliance document validator.
                    Analyze the provided data and return ONLY a valid JSON object.
                    No explanation. No markdown. No code blocks. Raw JSON only.""",
                    model=get_model(),
                )
                try:
                    response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                    result = json.loads(response)
                    proof_of_address_validation = AddressValidationResults(**result)
                    logger.info(f"[{AGENT_NAME}] Address validation: matches={proof_of_address_validation.overall_matches}")
                except Exception as exc:
                    logger.error(f"[{AGENT_NAME}] Address validation failed: {exc}")
                    proof_of_address_validation = AddressValidationResults(
                        overall_matches=False,
                        document_type="unknown",
                        is_full_name_matching=False,
                        is_full_address_matching=False,
                        analysis=f"Validation error: {exc}",
                        summary=f"Address validation failed: {exc}",
                        reason_for_unmatch="Unexpected error during validation.",
                        recommendation_for_unmatch="Re-run or contact support.",
                    )

            # Save to state
            state.identification_validation = identification_validation
            state.employment_validation = employment_validation
            state.proof_of_address_validation = proof_of_address_validation
            state.mark_step("run_document_validations")

            return {
                "status": "ok",
                "identification_validated": identification_validation.overall_matches if identification_validation else None,
                "employment_validated": employment_validation.overall_matches if employment_validation else None,
                "address_validated": proof_of_address_validation.overall_matches if proof_of_address_validation else None,
            }

        try:
            result = asyncio.run(_validate())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] run_document_validations failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 2: Check Data Completeness ───────────────────────────────────────
    @tool
    def check_data_completeness(party_id: str) -> str:
        """
        Check if all required data fields are present and complete
        using an internal LLM agent. Analyzes DataAnalystOutput and
        ActivityMonitorOutput together. Saves result to state.
        Must be called after run_document_validations.
        """
        async def _check():
            if not state.data_analyst_summary:
                return {"error": "DataAnalystOutput not in state.", "status": "failed"}
            if not state.activity_monitor_summary:
                return {"error": "ActivityMonitorOutput not in state.", "status": "failed"}

            prompt_template = await state.db.agent.get_agent_prompt(11.0)
            if not prompt_template:
                return {"error": "Data completeness prompt (11.0) not found.", "status": "failed"}

            # Slim down DA output to what prompt needs
            raw_pi = state.latest_kyc_party_info.model_dump()
            pi = raw_pi.get("party_info") or {}
            
            raw_ri = state.review_info.model_dump()
            ri = raw_ri.get("review_info") or {}
            
            raw_svoc = [s.model_dump() for s in (state.svoc_data or [])]

            da_slim = {
                "party_info": {"party_id": pi.get("party_id"), "party_name": pi.get("party_name")},
                "review_info": {
                    "review_id": ri.get("review_id"),
                    "full_name": ri.get("full_name"),
                    "date_of_birth": ri.get("date_of_birth"),
                    "country_of_birth": ri.get("country_of_birth"),
                    "country_of_residence": ri.get("country_of_residence"),
                    "country_of_citizenship": ri.get("country_of_citizenship"),
                    "employment_status": ri.get("employment_status"),
                    "address_line_1": ri.get("address_line_1"),
                    "post_code": ri.get("post_code"),
                },
                "svoc_data": [
                    {
                        "account_no": s.get("account_no"),
                        "nsc": s.get("nsc"),
                        "cash_percentage": s.get("cash_percentage"),
                        "turnover_selected": s.get("turnover_selected"),
                    }
                    for s in raw_svoc
                ],
            }

            am_slim = {
                "party_id": state.party_id,
                "account_summaries": state.suspicious_activity_results or [],
                "employment_results": state.employment_analysis_results or [],
                "transaction_analysis": state.country_risk_analysis,
            }

            prompt = prompt_template.format(
                da_output=json.dumps(da_slim, indent=2, default=str),
                am_output=json.dumps(am_slim, indent=2, default=str),
            )

            agent = Agent(
                system_prompt="""You are a data completeness analyst.
                Analyze the provided data and return ONLY a valid JSON object.
                No explanation. No markdown. No code blocks. Raw JSON only.""",
                model=get_model(),
            )

            try:
                response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                result = json.loads(response)
                state.data_completeness_check = result
                state.mark_step("check_data_completeness")
                logger.info(
                    f"[{AGENT_NAME}] Data completeness: is_complete={result.get('is_complete')}, "
                    f"missing={len(result.get('missing_fields', []))}"
                )
                return {"status": "ok", **result}
            except Exception as exc:
                logger.error(f"[{AGENT_NAME}] Data completeness check failed: {exc}")
                return {"status": "failed", "error": str(exc)}

        try:
            result = asyncio.run(_check())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] check_data_completeness failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 3: Save Compliance Summary ───────────────────────────────────────
    @tool
    def save_compliance_summary(party_id: str) -> str:
        """
        Build and save the compliance summary into pipeline state.
        Call this as the final step after all validations and completeness check.
        """
        id_val = state.identification_validation
        emp_val = state.employment_validation
        addr_val = state.proof_of_address_validation
        completeness = getattr(state, "data_completeness_check", {})

        def _pass_fail(val, key="overall_matches"):
            if val is None:
                return "SKIPPED"
            return "PASS" if getattr(val, key, False) else "FAIL"

        missing_fields = completeness.get("missing_fields", [])
        missing_text = ", ".join(missing_fields) if missing_fields else "None"
        ready = completeness.get("is_complete", False)

        summary = f"""
Compliance Agent Summary for Party ID: {party_id}

Validation Summary:
  - Identification:      {_pass_fail(id_val)}
  - Employment:          {_pass_fail(emp_val)}
  - Proof of Address:    {_pass_fail(addr_val)}
  - Data Completeness:   {'PASS' if ready else 'FAIL'}
  - Ready for ODD:       {'YES' if ready else 'NO'}

Data Completeness:
  - Is Complete: {ready}
  - Missing Fields: {missing_text}
  - Reason: {completeness.get('reason', 'N/A')}

Overall: {'All checks passed. Data is ready for ODD validation.' if ready else 'One or more checks failed. Remediation required before ODD validation.'}
""".strip()

        state.compliance_summary = summary
        state.mark_step("save_compliance_summary")

        logger.info(f"[{AGENT_NAME}] Compliance summary saved for party: {party_id}")
        return json.dumps({"status": "success", "party_id": party_id, "ready_for_odd": ready})


    return [
        run_document_validations,
        check_data_completeness,
        save_compliance_summary,
    ]