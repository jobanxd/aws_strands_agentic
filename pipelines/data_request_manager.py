"""
pipelines/data_request_manager.py
───────────────────────────────────
Data Request Manager super agent.

Orchestrates DataAnalystAgent → ActivityMonitorAgent → ComplianceAgent
in a strict sequence using plain Python — not LLM routing.

WHY PYTHON ORCHESTRATION (not LLM tool-calling for sequence)?
  LLM-driven sequencing works but can be inconsistent with weaker local models.
  Explicit Python sequencing is deterministic, easier to test, and easier to debug.
  Use LLM routing only when the sequence genuinely needs to be dynamic.
"""

from agents.drm_agents import DataAnalystAgent, ActivityMonitorAgent, ComplianceAgent
from utils.logger import logger
from utils.exceptions import InsufficientDataError, PipelineError


class DataRequestManager:
    """
    Super agent: Data Request Manager
    Runs sub-agents in order. Stops early if DataAnalystAgent
    raises InsufficientDataError.
    """

    def __init__(self):
        self.data_analyst = DataAnalystAgent()
        self.activity_monitor = ActivityMonitorAgent()
        self.compliance = ComplianceAgent()

    def run(self, query: str) -> str:
        """
        Executes the DRM pipeline. Returns the compliance report string.
        Raises InsufficientDataError to signal early exit to the orchestrator.
        """
        logger.info("DataRequestManager | pipeline start")

        # Step 1 — Data analyst (may raise InsufficientDataError)
        analyst_output = self.data_analyst.run(query)

        # Step 2 — Activity monitor receives analyst output
        monitor_input = f"Original query: {query}\n\nData analysis: {analyst_output}"
        monitor_output = self.activity_monitor.run(monitor_input)

        # Step 3 — Compliance receives combined context
        compliance_input = (
            f"Original query: {query}\n\n"
            f"Data analysis: {analyst_output}\n\n"
            f"Activity report: {monitor_output}"
        )
        compliance_output = self.compliance.run(compliance_input)

        logger.info("DataRequestManager | pipeline complete")
        return compliance_output
