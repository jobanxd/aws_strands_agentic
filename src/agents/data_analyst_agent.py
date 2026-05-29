"""Data Analyst Agent Main Config"""

import json

from dataclasses import asdict
from strands import Agent
from src.core.model_factory import get_model

from src.agents.state import PipelineState
from src.agents.tools.data_analyst_tools import make_tool
from src.utils.prompt_loader import get_prompt
from src.utils.exceptions import InsufficientDataError, PipelineError
from src.utils.logger import logger

AGENT_NAME = "Data Analyst Agent"
SYSTEM_PROMPT = get_prompt(
    category="system_prompts",
    module_name="data_analyst_prompt",
    prompt_name="DATA_ANALYST_SYSTEM_PROMPT",
)


class DataAnalystAgent:
    """
    Data Analyst Agent
        - Orchestrates all data extraction steps for party ODD review.
    """

    def __init__(self):
        self.model = get_model()
        self.system_prompt = SYSTEM_PROMPT
        logger.info(f"{AGENT_NAME} initialized")

    def run(self, state: PipelineState) -> PipelineState:
        """
        Runs the data analyst pipeline for the query in state.
        Mutates state directly (tools write to state as they execute).
        Returns the updated state.
        Raises InsufficientDataError if data cannot support further pipeline stages.
        """

        logger.info(f"{AGENT_NAME} starting")

        tools = make_tool(state)

        agent = Agent(
            system_prompt=self.system_prompt,
            tools=tools,
            model=self.model,
        )

        try:
            result = agent(state.query)
            with open("state_dump_after_data_analyst.txt", "w", encoding="utf-8") as f:
                json.dump(asdict(state), f, indent=2, default=str)
            logger.info(f"{AGENT_NAME} Completed. Result: {result}")
            logger.info(f"{AGENT_NAME} Completed. Steps: {state.steps_completed}")
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            raise PipelineError(f"DataAnalystAgent failed: {exc}") from exc

        if state.status in ("not_applicable", "insufficient_data"):
            raise InsufficientDataError(
                state.error_message or f"Pipeline halted at DataAnalystAgent: {state.status}"
            )

        return state
