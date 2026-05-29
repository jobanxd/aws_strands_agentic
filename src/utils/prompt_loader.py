"""Prompt Loader Utils"""

from importlib import import_module


def get_prompt(agent: str, prompt_name: str) -> str:
    """
    Example:
        get_prompt(
            "data_analyst_agent",
            "SYSTEM_PROMPT",
        )
    """

    try:
        module = import_module(
            f"src.agents.{agent}.prompts"
        )

    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"Prompt module not found for agent: '{agent}'"
        ) from exc

    try:
        return getattr(module, prompt_name)

    except AttributeError as exc:
        raise AttributeError(
            f"Prompt '{prompt_name}' not found "
            f"in {agent}.prompts"
        ) from exc
