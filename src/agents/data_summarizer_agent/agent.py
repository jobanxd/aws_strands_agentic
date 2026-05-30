"""Data Summarizer Agent Main Config"""

from strands import Agent
from src.core.model_factory import get_model

from src.workflows.state import PipelineState
from src.utils.prompt_loader import get_prompt
from src.utils.logger import get_logger

logger = get_logger(__name__)

AGENT_NAME = "Data Summarizer Agent"
SYSTEM_PROMPT = get_prompt(
    agent="data_summarizer_agent",
    prompt_name="DATA_SUMMARIZER_SYSTEM_PROMPT",
)


class DataSummarizerAgent:
    """
    Data Summarizer Agent
        - Summarizes data for ODD review
    """

    def __init__(self):
        self.model = get_model()
        self.system_prompt = SYSTEM_PROMPT
        logger.info(f"{AGENT_NAME} initialized")

    def run(self, state: PipelineState) -> PipelineState:
        logger.info(f"{AGENT_NAME} Running (stub)")
        state.mark_step("DataSummarizerAgent")
        return state


