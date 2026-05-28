"""
agents/drm_agents.py
─────────────────────
Data Request Manager sub-agents.

DataAnalystAgent uses the make_tools(state) factory so each tool
has direct access to the pipeline state without globals.
"""

from strands import Agent
from config.model_factory import get_model
from tools.data_analyst.data_analyst_tools import make_tools
from utils.state import PipelineState
from utils.exceptions import InsufficientDataError, PipelineError
from utils.logger import logger

AGENT_NAME = "Data Analyst"

DATA_ANALYST_SYSTEM_PROMPT = """
You are the Data Analyst Agent for the ODD (Ongoing Due Diligence) Review Process.

Your sole responsibility is to call tools in the exact sequence below to extract
all required data for a party review. Do not reason about the data. Do not skip,
reorder, or add steps. Call the next tool immediately after each success.

═══════════════════════════════════════════════
TOOL EXECUTION SEQUENCE
═══════════════════════════════════════════════

1. extract_party_id
2. fetch_kyc_data
3. fetch_svoc_data
4. fetch_servicelink_data
5. check_account_status
6. extract_previous_residence
7. save_analyst_output

═══════════════════════════════════════════════
RULES
═══════════════════════════════════════════════

- Always pass the bare numeric party ID to every tool. Never pass labels or prefixes.
  Correct: "1000001" — Wrong: "party_id:1000001"
- After each tool call, check the status before calling the next tool.
- If any tool returns a failed status, stop immediately and report the error.
- If check_account_status returns "not_applicable", stop immediately and return its result.
- Do not call extract_documents. It is not part of this pipeline.
- Do not narrate or explain between steps. Call the next tool immediately.
- Your final response must be the output of save_analyst_output.
"""


class DataAnalystAgent:
    """
    Data Analyst Agent — first in the DRM pipeline.
    Orchestrates all data extraction steps for a party ODD review.
    """

    def __init__(self):
        self._model = get_model()

    def run(self, state: PipelineState) -> PipelineState:
        """
        Runs the data analyst pipeline for the query in state.
        Mutates state directly (tools write to state as they execute).
        Returns the updated state.
        Raises InsufficientDataError if data cannot support further pipeline stages.

        NOTE: InsufficientDataError thrown inside a @tool is caught by Strands internally
        and will NOT propagate out of agent(). Instead we check state.status after the
        call — tools set this flag before raising so we always detect early exits.
        """
        logger.info(f"[{AGENT_NAME}] Starting for query: {state.query}")

        # Attach an early-exit flag to state so tools can signal halts
        # without relying on exception propagation through Strands
        state._early_exit = False
        state._early_exit_reason = None

        tools = make_tools(state)

        agent = Agent(
            system_prompt=DATA_ANALYST_SYSTEM_PROMPT,
            tools=tools,
            model=self._model,
        )

        try:
            result = agent(state.query)
            logger.info(f"[{AGENT_NAME}] Completed. Steps: {state.steps_completed}")
        except Exception as exc:
            logger.error(f"[{AGENT_NAME}]] Unexpected error: {exc}")
            raise PipelineError(f"DataAnalystAgent failed: {exc}") from exc

        # Check state flags set by tools — this is how we detect early exits
        if getattr(state, "_early_exit", False):
            reason = getattr(state, "_early_exit_reason", "Insufficient data")
            logger.warning("[{AGENT_NAME}] Early exit flagged: {reason}")
            raise InsufficientDataError(reason)

        if state.status in ("not_applicable", "insufficient_data"):
            raise InsufficientDataError(
                state.error_message or f"Pipeline halted at DataAnalystAgent: {state.status}"
            )

        return state


class ActivityMonitorAgent:
    """Stub — implement next using same make_tools pattern."""

    def run(self, state: PipelineState) -> PipelineState:
        logger.info("[ActivityMonitor] Running (stub)")
        state.mark_step("ActivityMonitorAgent")
        return state


class ComplianceAgent:
    """Stub — implement next using same make_tools pattern."""

    def run(self, state: PipelineState) -> PipelineState:
        logger.info("[Compliance] Running (stub)")
        state.mark_step("ComplianceAgent")
        return state
