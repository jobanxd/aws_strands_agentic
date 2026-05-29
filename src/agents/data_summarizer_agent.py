"""Compliance Agent Main Config"""

from strands import Agent
from src.core.model_factory import get_model

from src.agents.state import PipelineState
from src.utils.prompt_loader import get_prompt
from src.utils.logger import logger

AGENT_NAME = "Data Summarizer Agent"
SYSTEM_PROMPT = get_prompt(
    category="system_prompts",
    module_name="data_summarizer_prompt",
    prompt_name="DATA_SUMMARIZER_SYSTEM_PROMPT",
)


class DataSummarizerAgent:
    """
    Activity Monitor Agent
        - Orchestrates all compliance checks before proceeding to ODD process
    """

    def __init__(self):
        self.model = get_model()
        self.system_prompt = SYSTEM_PROMPT
        logger.info(f"{AGENT_NAME} initialized")

    def run(self, state: PipelineState) -> PipelineState:
        logger.info(f"{AGENT_NAME} Running (stub)")
        state.mark_step("DataSummarizerAgent")
        return state


