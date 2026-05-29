"""
utils/exceptions.py
────────────────────
Custom exceptions for pipeline control flow.
Using exceptions (not return codes) keeps agent code clean
and lets the orchestrator catch specific failure modes.
"""


class InsufficientDataError(Exception):
    """
    Raised by DataAnalystAgent when there is not enough data
    to continue the pipeline. The orchestrator catches this
    and halts processing — no further agents are called.
    """
    pass


class ValidationError(Exception):
    """
    Raised by VerifierAgent when the final output
    fails validation checks.
    """
    pass


class PipelineError(Exception):
    """
    Generic pipeline failure. Wraps unexpected errors
    so the orchestrator always gets a typed exception.
    """
    pass
