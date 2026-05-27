"""
agents/base_agent.py
─────────────────────
Thin base class every agent inherits from.
Handles model wiring, logging, and error wrapping in one place
so individual agents stay focused on their own logic.
"""

from strands import Agent
from config.model_factory import get_model
from utils.logger import logger
from utils.exceptions import PipelineError


class BaseAgent:
    """
    All agents inherit from this.
    Subclasses define:
      - SYSTEM_PROMPT  (str)  — the agent's role and instructions
      - TOOLS          (list) — tools this agent is allowed to use
    """

    SYSTEM_PROMPT: str = "You are a helpful assistant."
    TOOLS: list = []

    def __init__(self):
        self._agent = Agent(
            system_prompt=self.SYSTEM_PROMPT,
            tools=self.TOOLS,
            model=get_model(),
        )
        logger.info(f"{self.__class__.__name__} initialised")

    def run(self, query: str) -> str:
        """
        Runs the agent with the given query.
        Always returns a string. Wraps unexpected errors in PipelineError
        so callers always get a typed exception.
        """
        logger.info(f"{self.__class__.__name__} | input: {query[:80]}...")
        try:
            result = self._agent(query)
            output = str(result)
            logger.info(f"{self.__class__.__name__} | output: {output[:80]}...")
            return output
        except Exception as exc:
            # Re-raise typed pipeline exceptions as-is
            # so orchestrator can catch them specifically
            from utils.exceptions import InsufficientDataError, ValidationError
            if isinstance(exc, (InsufficientDataError, ValidationError, PipelineError)):
                raise
            raise PipelineError(
                f"{self.__class__.__name__} failed: {exc}"
            ) from exc
