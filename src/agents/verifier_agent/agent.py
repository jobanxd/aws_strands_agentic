"""Verifier Agent Main Config"""

from strands import Agent
from src.core.model_factory import get_model

from src.workflows.state import PipelineState
from src.utils.prompt_loader import get_prompt
from src.utils.logger import logger

AGENT_NAME = "Verifier Agent"
SYSTEM_PROMPT = get_prompt(
    agent="verifier_agent",
    prompt_name="VERIFIER_SYSTEM_PROMPT",
)


class VerifierAgent:
    """
    Verifier Agent
        - Verifies compliance before proceeding to ODD process
    """

    def __init__(self):
        self.model = get_model()
        self.system_prompt = SYSTEM_PROMPT
        logger.info(f"{AGENT_NAME} initialized")

    def run(self, state: PipelineState) -> PipelineState:
        logger.info(f"{AGENT_NAME} Running (stub)")
        state.mark_step("VerifierAgent")
        return state


