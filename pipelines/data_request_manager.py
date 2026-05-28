"""
pipelines/data_request_manager.py
───────────────────────────────────
Data Request Manager super agent.
Sequences: DataAnalystAgent → ActivityMonitorAgent → ComplianceAgent.
Passes PipelineState through each agent — no string concatenation.
"""

from agents.drm_agents import DataAnalystAgent, ActivityMonitorAgent, ComplianceAgent
from utils.state import PipelineState
from utils.exceptions import InsufficientDataError, PipelineError
from utils.logger import logger


class DataRequestManager:

    def __init__(self):
        self.data_analyst = DataAnalystAgent()
        self.activity_monitor = ActivityMonitorAgent()
        self.compliance = ComplianceAgent()

    def run(self, state: PipelineState) -> PipelineState:
        logger.info("DataRequestManager | pipeline start")

        # Step 1 — may raise InsufficientDataError (early exit signal)
        state = self.data_analyst.run(state)
        state = self.activity_monitor.run(state)
        state = self.compliance.run(state)

        logger.info("DataRequestManager | pipeline complete")
        return state
