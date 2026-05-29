"""Activity Monitor Agent Main Config"""

import json

from dataclasses import asdict
from strands import Agent

from src.core.model_factory import get_model
from src.workflows.state import PipelineState
from src.agents.activity_monitor_agent.tools import make_tools
from src.utils.prompt_loader import get_prompt
from src.utils.exceptions import PipelineError
from src.utils.logger import logger

AGENT_NAME = "Activity Monitor Agent"
SYSTEM_PROMPT = get_prompt(
    agent="activity_monitor_agent",
    prompt_name="ACTIVITY_MONITOR_SYSTEM_PROMPT",
)


class ActivityMonitorAgent:
    """
    Activity Monitor Agent
        - Orchestrates all transaction history analysis
    """

    def __init__(self):
        self.model = get_model()
        self.system_prompt = SYSTEM_PROMPT
        logger.info(f"{AGENT_NAME} initialized")

    def run(self, state: PipelineState) -> PipelineState:
        """
        Runs the activity monitor pipeline and continue the process in state.
        Mutates state directly (tools write to state as they execute).
        Returns the updated state.
        """

        logger.info(f"{AGENT_NAME} starting")

        tools = make_tools(state)

        agent = Agent(
            system_prompt=self.system_prompt,
            tools=tools,
            model=self.model,
        )

        try:
            result = agent(state.query)
            with open("state_dump_after_activity_monitor.txt", "w", encoding="utf-8") as f:
                json.dump(asdict(state), f, indent=2, default=str)
            logger.info(f"{AGENT_NAME} Completed. Result: {result}")
            logger.info(f"{AGENT_NAME} Completed. Steps: {state.steps_completed}")
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            raise PipelineError(f"ActivityMonitorAgent failed: {exc}") from exc

        return state
