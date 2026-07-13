import json
import asyncio

from strands import Agent
from strands import tool

from src.core.model_factory import get_model
from src.workflows.state import PipelineState
from src.utils.logger import get_logger
from src.utils.prompt_loader import get_prompt

logger = get_logger(__name__)
AGENT_NAME = "Verifier Agent"


def make_tools(state: PipelineState) -> list:

    @tool
    def verify_odd_report(party_id: str) -> str:
        """
        Verify the final ODD report for completeness and correctness
        using an internal LLM agent with prompt 15.0.
        Checks all fields are populated and valid.
        Saves verification result to state.
        Must be called first.
        """
        async def _verify():
            if not state.fe_final_report:
                return {"error": "Final report not in state. DataSummarizer must run first.", "status": "failed"}

            # prompt_template = await state.db.agent.get_agent_prompt(15.0)
            prompt_template = get_prompt(
                agent="verifier_agent",
                prompt_name="VERIFY_COMPLETENESS_PROMPT",
            )
            if not prompt_template:
                return {"error": "Verify KYC form prompt (15.0) not found.", "status": "failed"}

            prompt = prompt_template.replace(
                "{kyc_form_data}",
                json.dumps(state.fe_final_report, indent=2, default=str)
            )

            agent = Agent(
                system_prompt="""You are a KYC report verifier.
                Analyze the provided report and return ONLY a valid JSON object.
                No explanation. No markdown. No code blocks. Raw JSON only.""",
                model=get_model(),
            )

            try:
                response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                result = json.loads(response)
                state.verification_result = result
                state.mark_step("verify_odd_report")
                logger.info(
                    f"[{AGENT_NAME}] Verification complete: "
                    f"is_validated={result.get('is_validated')}, "
                    f"missing={len(result.get('missing_fields', []))}"
                )
                return {"status": "ok", **result}
            except Exception as exc:
                logger.error(f"[{AGENT_NAME}] Verification failed: {exc}")
                return {
                    "status": "failed",
                    "is_validated": False,
                    "missing_fields": ["error_verification"],
                    "reason": str(exc),
                }

        try:
            result = asyncio.run(_verify())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] verify_odd_report failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 2: Mark Review Completed ─────────────────────────────────────────
    @tool
    def mark_review_completed(party_id: str) -> str:
        """
        Mark the review as completed in the SharePoint list.
        Only call this if verify_odd_report returned is_validated = true.
        Updates the review status to 'Completed' with the new review ID.
        """
        async def _mark():
            if not state.review_info:
                return {"error": "DataAnalystOutput not in state.", "status": "failed"}

            old_review_id = state.review_info.review_id if state.review_info else None
            new_review_id = state.new_review_id

            if not old_review_id or not new_review_id:
                return {"error": "Missing review IDs in state.", "status": "failed"}

            try:
                success = await state.db.sharepoint.update_review_status_completed(
                    party_id, old_review_id, new_review_id
                )
                state.mark_step("mark_review_completed")
                if success:
                    logger.info(f"[{AGENT_NAME}] Review marked completed: {old_review_id} → {new_review_id}")
                    return {"status": "ok", "marked_completed": True}
                else:
                    logger.warning(f"[{AGENT_NAME}] No matching record found to mark completed")
                    return {"status": "ok", "marked_completed": False, "warning": "No matching record found"}
            except Exception as exc:
                logger.error(f"[{AGENT_NAME}] mark_review_completed DB error: {exc}")
                return {"status": "failed", "error": str(exc)}

        try:
            result = asyncio.run(_mark())
            return json.dumps(result)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] mark_review_completed failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 3: Save Verifier Summary ─────────────────────────────────────────
    @tool
    def save_verifier_summary(party_id: str) -> str:
        """
        Build and save the verifier summary into pipeline state.
        Call this as the final step always, regardless of validation outcome.
        """
        verification_result = getattr(state, "verification_result", {})
        is_validated = verification_result.get("is_validated", False)
        missing_fields = verification_result.get("missing_fields", [])

        missing_text = "\n".join([f"  - {f}" for f in missing_fields[:10]]) if missing_fields else "  None"
        more_text = "  ..." if len(missing_fields) > 10 else ""
        status_text = "VALIDATED - Ready for UI" if is_validated else "NOT VALIDATED - Missing Fields"
        next_action = (
            "NEXT ACTION: Display KYC form in UI."
            if is_validated
            else "NEXT ACTION: Retry Data Summarizer to complete missing fields."
        )

        summary = f"""
Verifier Agent Report for Party ID: {party_id}

KYC FORM VERIFICATION {'COMPLETE' if is_validated else 'INCOMPLETE'}

Validation Status: {status_text}

Missing Fields ({len(missing_fields)}):
{missing_text}
{more_text}

Reason: {verification_result.get('reason', 'N/A')}

{next_action}
""".strip()

        state.verifier_summary = summary
        state.mark_step("save_verifier_summary")

        logger.info(f"[{AGENT_NAME}] Verifier summary saved for party: {party_id}")
        return json.dumps({
            "status": "success",
            "party_id": party_id,
            "is_validated": is_validated,
        })


    return [
        verify_odd_report,
        mark_review_completed,
        save_verifier_summary,
    ]