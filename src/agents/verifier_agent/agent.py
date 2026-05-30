"""Verifier Agent Main Config"""

import json

from dataclasses import asdict
from strands import Agent

from src.core.model_factory import get_model
from src.workflows.state import PipelineState
from src.agents.verifier_agent.tools import make_tools
from src.utils.prompt_loader import get_prompt
from src.utils.exceptions import PipelineError
from src.utils.logger import get_logger

logger = get_logger(__name__)

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
        """
        Runs the verifier agent pipeline and continue the process in state.
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
            agent(state.query)
            with open("state_dump_after_verifier.txt", "w", encoding="utf-8") as f:
                json.dump(asdict(state), f, indent=2, default=str)
            logger.info(f"{AGENT_NAME} Completed. Steps: {state.steps_completed}")
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            raise PipelineError(f"VerifierAgent failed: {exc}") from exc

        return state
