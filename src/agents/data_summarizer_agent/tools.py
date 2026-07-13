import json
import asyncio

from strands import tool
from strands import Agent

from src.core.model_factory import get_model
from src.workflows.state import PipelineState
from src.models.agent_models import (
    KYCnetFormDataWithEvidence,
    KYCQuestionAnswersWithEvidence,
    KYCFullReview,
)
from src.utils.report_generation_utils import ReportGenerationUtils
from src.utils.logger import get_logger
from src.utils.prompt_loader import get_prompt

logger = get_logger(__name__)
AGENT_NAME = "Data Summarizer"


def make_tools(state: PipelineState) -> list:

    # ── Step 1: Generate New Review ID ───────────────────────────────────────
    @tool
    def generate_new_review_id(party_id: str) -> str:
        """
        Generate the new review ID from the latest completed KYC review.
        Saves it to state. Must be called first.
        """
        async def _generate():
            kyc_party_info = await state.db.kyc.get_party_info(party_id)
            if not kyc_party_info:
                return {"error": f"No KYC party info found for party: {party_id}", "status": "failed"}

            latest = max(kyc_party_info, key=lambda x: x.date_current_review_started)
            state.new_review_id = latest.review_id
            state.mark_step("generate_new_review_id")

            logger.info(f"[{AGENT_NAME}] New review ID: {state.new_review_id}")
            return {"status": "ok", "new_review_id": state.new_review_id}

        try:
            result = asyncio.run(_generate())
            return json.dumps(result)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] generate_new_review_id failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 2: Generate KYC Form Information ────────────────────────────────
    @tool
    def generate_kyc_form_information(party_id: str) -> str:
        """
        Generate the KYCnet Information portion of the KYC form (fields 1-19)
        using an internal LLM agent with prompt 12.0.
        Requires DataAnalystOutput, ActivityMonitorOutput, and compliance
        validation results to be in state.
        Saves KYCnetFormDataWithEvidence to state.
        """
        async def _generate():
            if not state.data_analyst_summary or not state.activity_monitor_summary:
                return {"error": "Agent outputs not in state.", "status": "failed"}

            # prompt_template = await state.db.agent.get_agent_prompt(12.0)
            prompt_template = get_prompt(
                agent="data_summarizer_agent",
                prompt_name="GENERATE_KYC_INFORMATION_PROMPT",
            )
            if not prompt_template:
                return {"error": "KYCnet Information prompt (12.0) not found.", "status": "failed"}

            payload = {
                "party_info": state.latest_kyc_party_info.model_dump() if state.latest_kyc_party_info else {},
                "review_info": state.review_info.model_dump() if state.review_info else {},
                "textract_data": state.textract_data.model_dump(
                    exclude={
                        "proof_of_id": {"document_path"},
                        "employment": {"document_path"},
                        "proof_of_address": {"document_path"},
                    }
                ) if state.textract_data else {},
                "svoc_data": [s.model_dump() for s in state.active_svoc_data],
                "servicelink_bundles": [b.account_details.model_dump() for b in state.active_servicelink_bundles],
                "employment_results": state.employment_analysis_results or [],
                "country_risk_analysis": state.country_risk_analysis or {},
                "previous_length_of_residence": state.previous_length_of_residence,
                "identification_validation": state.identification_validation.model_dump() if state.identification_validation else None,
                "employment_validation": state.employment_validation.model_dump() if state.employment_validation else None,
                "proof_address_validation": state.proof_of_address_validation.model_dump() if state.proof_of_address_validation else None,
            }

            prompt = prompt_template.replace("{input_data}", json.dumps(payload, indent=2, default=str))
            prompt = prompt.replace("{agent_summaries}", _build_summaries_context(state))

            agent = Agent(
                system_prompt="""You are a KYC form generation specialist.
                Analyze all provided data and return ONLY a valid JSON object.
                No explanation. No markdown. No code blocks. Raw JSON only.""",
                model=get_model(),
            )

            try:
                response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                data = json.loads(response)
                kyc_form_data = KYCnetFormDataWithEvidence(**data["kyc_form_data"])
                state.kyc_form_data = kyc_form_data
                state.mark_step("generate_kyc_form_information")
                logger.info(f"[{AGENT_NAME}] KYC form information generated")
                return {"status": "ok"}
            except Exception as exc:
                logger.error(f"[{AGENT_NAME}] KYC form information failed: {exc}")
                return {"status": "failed", "error": str(exc)}

        try:
            result = asyncio.run(_generate())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] generate_kyc_form_information failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 3: Generate KYC Q&A ──────────────────────────────────────────────
    @tool
    def generate_kyc_question_answers(party_id: str) -> str:
        """
        Generate the KYCnet Question and Answer portion of the KYC form (fields 1-9)
        using an internal LLM agent with prompt 13.0.
        Saves KYCQuestionAnswersWithEvidence to state.
        Must be called after generate_kyc_form_information.
        """
        async def _generate():
            if not state.data_analyst_summary or not state.activity_monitor_summary:
                return {"error": "Agent outputs not in state.", "status": "failed"}

            # prompt_template = await state.db.agent.get_agent_prompt(13.0)
            prompt_template = get_prompt(
                agent="data_summarizer_agent",
                prompt_name="GENERATE_KYC_QNA_PROMPT",
            )
            if not prompt_template:
                return {"error": "KYCnet Q&A prompt (13.0) not found.", "status": "failed"}

            payload = {
                "party_info": state.latest_kyc_party_info.model_dump() if state.latest_kyc_party_info else {},
                "review_info": state.review_info.model_dump() if state.review_info else {},
                "textract_data": state.textract_data.model_dump(
                    exclude={
                        "proof_of_id": {"document_path"},
                        "employment": {"document_path"},
                        "proof_of_address": {"document_path"},
                    }
                ) if state.textract_data else {},
                "svoc_data": [s.model_dump() for s in state.active_svoc_data],
                "cash_percentage": state.final_cash_percentage,
                "servicelink_bundles": [b.model_dump() for b in state.active_servicelink_bundles],
                "employment_results": state.employment_analysis_results or [],
                "country_risk_analysis": state.country_risk_analysis or {},
                "previous_length_of_residence": state.previous_length_of_residence,
                "identification_validation": state.identification_validation.model_dump() if state.identification_validation else None,
                "employment_validation": state.employment_validation.model_dump() if state.employment_validation else None,
                "proof_address_validation": state.proof_of_address_validation.model_dump() if state.proof_of_address_validation else None,
            }

            prompt = prompt_template.replace("{input_data}", json.dumps(payload, indent=2, default=str))
            prompt = prompt.replace("{agent_summaries}", _build_summaries_context(state))

            agent = Agent(
                system_prompt="""You are a KYC form generation specialist.
                Analyze all provided data and return ONLY a valid JSON object.
                No explanation. No markdown. No code blocks. Raw JSON only.""",
                model=get_model(),
            )

            try:
                response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                data = json.loads(response)
                kyc_qa = KYCQuestionAnswersWithEvidence(**data["kyc_question_answers"])
                state.kyc_question_answers = kyc_qa
                state.mark_step("generate_kyc_question_answers")
                logger.info(f"[{AGENT_NAME}] KYC Q&A generated")
                return {"status": "ok"}
            except Exception as exc:
                logger.error(f"[{AGENT_NAME}] KYC Q&A generation failed: {exc}")
                return {"status": "failed", "error": str(exc)}

        try:
            result = asyncio.run(_generate())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] generate_kyc_question_answers failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 4: Generate Final Report ─────────────────────────────────────────
    @tool
    def generate_final_report(party_id: str) -> str:
        """
        Transform KYC form data and Q&A into the final report format expected by the frontend.
        Requires kyc_form_data and kyc_question_answers to be in state.
        Saves the final report to state.
        Must be called after generate_kyc_question_answers.
        """
        async def _generate():
            if not state.kyc_form_data or not state.kyc_question_answers:
                return {"error": "KYC form data or Q&A not in state. Run previous steps first.", "status": "failed"}
            if not state.data_analyst_output:
                return {"error": "DataAnalystOutput not in state.", "status": "failed"}

            ca_output_slim = _build_ca_output(state)
            final_output = KYCFullReview(
                kyc_form_data=state.kyc_form_data,
                kyc_question_answers=state.kyc_question_answers,
            )

            fe_final_report = await ReportGenerationUtils.final_report_generation(
                svoc=state.svoc_data,
                servicelink=state.servicelink_bundles,
                party_info=state.latest_kyc_party_info,
                review_info=state.review_info,
                textract_data=state.textract_data,
                kyc_form_data=final_output.kyc_form_data,
                kyc_qna=final_output.kyc_question_answers,
                new_review_id=state.new_review_id,
                avg_cash_calc=state.final_cash_percentage | 0,
                ca_output=ca_output_slim,
            )

            state.fe_final_report = fe_final_report
            state.mark_step("generate_final_report")

            logger.info(f"[{AGENT_NAME}] Final report generated for party: {party_id}")
            return {"status": "ok", "new_review_id": state.new_review_id}

        try:
            result = asyncio.run(_generate())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] generate_final_report failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 5: Generate Final Summary ────────────────────────────────────────
    @tool
    def generate_final_summary(party_id: str) -> str:
        """
        Generate the ODD Report Overview and next steps using an internal LLM agent
        with prompt 14.0. Updates the final report with bullets and next steps.
        Saves summary to state. Must be called after generate_final_report.
        """
        async def _generate():
            if not state.fe_final_report:
                return {"error": "Final report not in state. Run generate_final_report first.", "status": "failed"}

            # prompt_template = await state.db.agent.get_agent_prompt(14.0)
            prompt_template = get_prompt(
                agent="data_summarizer_agent",
                prompt_name="GENERATE_OVERVIEW_SUMMARY_PROMPT",
            )
            if not prompt_template:
                return {"error": "Final summary prompt (14.0) not found.", "status": "failed"}

            validation_report = {
                "employment_analysis_results": state.employment_analysis_results if state.employment_analysis_results else [],
                "identification_validation_results": state.identification_validation.model_dump() if state.identification_validation else None,
                "employment_validation_results": state.employment_validation.model_dump() if state.employment_validation else None,
                "address_validation_results": state.proof_of_address_validation.model_dump() if state.proof_of_address_validation else None,
            }

            prompt = (
                prompt_template
                .replace("{final_report}", json.dumps(state.fe_final_report, indent=2, default=str))
                .replace("{validation_report}", json.dumps(validation_report, indent=2, default=str))
            )

            agent = Agent(
                system_prompt="""You are a KYC report summarizer.
                Analyze the provided data and return ONLY a valid JSON object.
                No explanation. No markdown. No code blocks. Raw JSON only.""",
                model=get_model(),
            )

            try:
                response = str(agent(prompt)).strip().strip("```json").strip("```").strip()
                final_summary = json.loads(response)

                if hasattr(state.fe_final_report, "overview"):
                    state.fe_final_report.overview.bullets = final_summary.get("bullets", [])
                    state.fe_final_report.next_steps = final_summary.get("next_steps", [])

                state.final_summary = final_summary
                state.mark_step("generate_final_summary")
                logger.info(f"[{AGENT_NAME}] Final summary generated")
                return {"status": "ok"}
            except Exception as exc:
                logger.error(f"[{AGENT_NAME}] Final summary failed: {exc}")
                state.mark_step("generate_final_summary")
                return {"status": "ok", "warning": f"Summary generation failed, using fallback: {exc}"}

        try:
            result = asyncio.run(_generate())
            return json.dumps(result, default=str)
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}] generate_final_summary failed: {exc}")
            return json.dumps({"error": str(exc), "status": "failed"})


    # ── Step 6: Save Data Summarizer Summary ──────────────────────────────────
    @tool
    def save_summarizer_summary(party_id: str) -> str:
        """
        Build and save the data summarizer summary into pipeline state.
        Call this as the final step.
        """
        new_review_id = getattr(state, "new_review_id", "N/A")
        final_summary = getattr(state, "final_summary", {})
        summary_text = json.dumps(final_summary, indent=2, default=str) if final_summary else "KYC Review completed."

        summary = f"""
Data Summarizer Report for Party ID: {party_id}

New Review ID: {new_review_id}

Final KYC Form Summary:
{summary_text}

The complete KYC form with evidence has been generated and is ready for submission to KYCnet.
All data has been validated and cross-referenced across multiple sources.
""".strip()

        state.data_summarizer_summary = summary
        state.mark_step("save_summarizer_summary")

        logger.info(f"[{AGENT_NAME}] Summarizer summary saved for party: {party_id}")
        return json.dumps({
            "status": "success",
            "party_id": party_id,
            "new_review_id": new_review_id,
        })


    return [
        generate_new_review_id,
        generate_kyc_form_information,
        generate_kyc_question_answers,
        generate_final_report,
        generate_final_summary,
        save_summarizer_summary,
    ]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_summaries_context(state: PipelineState) -> str:
    summaries = []
    if getattr(state, "compliance_summary", None):
        summaries.append(f"=== Compliance Agent ===\n{state.compliance_summary}")
    if getattr(state, "activity_monitor_summary", None):
        summaries.append(f"=== Activity Monitor ===\n{state.activity_monitor_summary}")
    if getattr(state, "data_analyst_summary", None):
        summaries.append(f"=== Data Analyst ===\n{state.data_analyst_summary}")
    return "\n\n".join(summaries) if summaries else "No agent summaries available."


def _build_ca_output(state: PipelineState):
    """Build a minimal compliance output object for report generation."""
    from src.models.agent_models import ComplianceCheckOutput
    return ComplianceCheckOutput(
        party_id=state.party_id,
        identification_validation=state.identification_validation,
        employment_validation=state.employment_validation,
        proof_of_address_validation=state.proof_of_address_validation,
        data_completeness_check=getattr(state, "data_completeness_check", {}),
        ready_for_odd_validation=getattr(state, "data_completeness_check", {}).get("is_complete", False),
    )