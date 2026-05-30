"""
Data Request Manager Agent
Sequences: DataAnalystAgent → ActivityMonitorAgent → ComplianceAgent.
Passes PipelineState through each agent.
"""

from src.agents.data_summarizer_agent.agent import DataSummarizerAgent
from src.agents.verifier_agent.agent import VerifierAgent
from src.workflows.state import PipelineState
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ODDValidator:

    def __init__(self):
        self.data_summarizer = DataSummarizerAgent()
        self.verifier = VerifierAgent()

    def run(self, state: PipelineState) -> PipelineState:
        logger.info("ODDValidator | pipeline start")

        # Step 1 — may raise InsufficientDataError (early exit signal)
        state = self.data_summarizer.run(state)
        state = self.verifier.run(state)

        logger.info("ODDValidator | pipeline complete")
        return state
