"""
agents/base_agent.py
─────────────────────
Thin base class for simple string-in / string-out agents (ODD sub-agents).
DataAnalystAgent does NOT use this — it manages its own agent instantiation
via make_tools(state).
"""

from strands import Agent
from config.model_factory import get_model
from utils.logger import logger
from utils.exceptions import PipelineError


class BaseAgent:
    SYSTEM_PROMPT: str = "You are a helpful assistant."
    TOOLS: list = []

    def __init__(self):
        self._agent = Agent(
            system_prompt=self.SYSTEM_PROMPT,
            tools=self.TOOLS,
            model=get_model(),
        )
        logger.info(f"{self.__class__.__name__} initialised")

    def run(self, query) -> str:
        """
        Accepts a string query or a PipelineState.
        Always returns a string.
        """
        # Normalise input — accept string or PipelineState
        if hasattr(query, "query"):
            # It's a PipelineState — extract the string query
            prompt = query.query
        else:
            prompt = str(query)

        preview = prompt[:80]
        logger.info(f"{self.__class__.__name__} | input: {preview}...")

        try:
            result = self._agent(prompt)
            output = str(result)
            logger.info(f"{self.__class__.__name__} | output: {output[:80]}...")
            return output
        except Exception as exc:
            from utils.exceptions import InsufficientDataError, ValidationError
            if isinstance(exc, (InsufficientDataError, ValidationError, PipelineError)):
                raise
            raise PipelineError(f"{self.__class__.__name__} failed: {exc}") from exc
