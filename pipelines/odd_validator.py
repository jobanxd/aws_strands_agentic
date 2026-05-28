"""
pipelines/odd_validator.py
───────────────────────────
ODD Validator super agent.
Accepts PipelineState from DRM, passes the analyst summary into sub-agents.
"""

import logging
from agents.odd_agents import DataSummarizerAgent, VerifierAgent
from utils.state import PipelineState
from utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ODDValidator:

    def __init__(self):
        self.summarizer = DataSummarizerAgent()
        self.verifier = VerifierAgent()

    def run(self, state: PipelineState) -> PipelineState:
        logger.info("ODDValidator | pipeline start")

        # Pull the analyst summary out of state as a string for the sub-agents
        if state.data_analyst_output and state.data_analyst_output.summary:
            drm_summary = state.data_analyst_output.summary
        else:
            drm_summary = f"Data analyst completed for party_id: {state.party_id}"

        # Step 1 — Summarise
        summarized = self.summarizer.run(drm_summary)

        # Step 2 — Verify
        verified = self.verifier.run(f"Summary to verify:\n\n{summarized}")

        # Write back to state
        if state.data_analyst_output:
            state.data_analyst_output.summary = verified

        logger.info("ODDValidator | pipeline complete")
        return state
