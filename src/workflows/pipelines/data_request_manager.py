"""
Data Request Manager Agent
Sequences: DataAnalystAgent → ActivityMonitorAgent → ComplianceAgent.
Passes PipelineState through each agent.
"""

from src.agents.data_analyst_agent.agent import DataAnalystAgent
from src.agents.activity_monitor_agent.agent import ActivityMonitorAgent
from src.agents.compliance_agent.agent import ComplianceAgent
from src.workflows.state import PipelineState
from src.utils.logger import get_logger

logger = get_logger(__name__)


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
