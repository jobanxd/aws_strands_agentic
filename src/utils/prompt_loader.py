"""Load Agent Prompts (System/Tool Instruction)"""

from importlib import import_module


def get_prompt(category: str, module_name: str, prompt_name: str) -> str:
    """
    Example:
        get_prompt(
            "system_prompts",
            "data_analyst_prompt",
            "DATA_ANALYST_SYSTEM_PROMPT",
        )
    """

    module = import_module(
        f"src.agents.prompts.{category}.{module_name}"
    )

    return getattr(module, prompt_name)