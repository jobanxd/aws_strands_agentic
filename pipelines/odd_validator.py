"""
pipelines/odd_validator.py
───────────────────────────
ODD Validator super agent.

Orchestrates DataSummarizerAgent → VerifierAgent in sequence.
Receives the full DRM output as input.
"""

from agents.odd_agents import DataSummarizerAgent, VerifierAgent
from utils.logger import logger
from utils.exceptions import ValidationError


class ODDValidator:
    """
    Super agent: ODD Validator
    Summarises and verifies the DRM output.
    """

    def __init__(self):
        self.summarizer = DataSummarizerAgent()
        self.verifier = VerifierAgent()

    def run(self, drm_output: str) -> str:
        """
        Executes the ODD validation pipeline.
        Returns the verified summary string.
        Raises ValidationError if verification fails.
        """
        logger.info("ODDValidator | pipeline start")

        # Step 1 — Summarise the DRM output
        summary = self.summarizer.run(drm_output)

        # Step 2 — Verify the summary
        verify_input = f"Summary to verify:\n\n{summary}"
        verified = self.verifier.run(verify_input)

        logger.info("ODDValidator | pipeline complete")
        return verified
