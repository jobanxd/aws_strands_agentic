"""
agents/odd_agents.py
─────────────────────
Sub-agents owned by the ODD Validator super agent.
"""

from agents.base_agent import BaseAgent
from tools.data_tools import summarize_dataset, verify_output
from utils.exceptions import ValidationError
from utils.logger import logger


class DataSummarizerAgent(BaseAgent):
    """
    First in the ODD pipeline.
    Condenses the full DRM output into a clean summary.
    """

    SYSTEM_PROMPT = """
    You are a Data Summarizer Agent.

    You receive a detailed compliance and activity report.
    Your responsibilities:
    1. Use summarize_dataset to produce a concise, structured summary.
    2. Preserve all key findings, flags, and compliance outcomes.
    3. Return the summary in a clear, readable format.

    Do not omit any compliance violations or activity flags.
    """

    TOOLS = [summarize_dataset]


class VerifierAgent(BaseAgent):
    """
    Second in the ODD pipeline.
    Verifies the summarizer's output for quality and accuracy.
    Raises ValidationError if verification fails.
    """

    SYSTEM_PROMPT = """
    You are a Verifier Agent.

    You receive a summary from the Data Summarizer.
    Your responsibilities:
    1. Use verify_output to check the summary for accuracy and completeness.
    2. If verification passes, return the verified summary with a confidence score.
    3. If verification fails, clearly state: "VERIFICATION FAILED: <reason>"

    Do not pass incomplete or inaccurate summaries.
    """

    TOOLS = [verify_output]

    def run(self, query: str) -> str:
        result = super().run(query)

        if result.strip().upper().startswith("VERIFICATION FAILED"):
            logger.error(f"VerifierAgent | validation failed: {result}")
            raise ValidationError(result)

        return result
