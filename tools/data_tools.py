"""
tools/data_tools.py
────────────────────
External tool functions available to sub-agents.
Each @tool is a concrete capability: DB query, API call, file read, etc.
Sub-agents are given only the tools they actually need.

BEST PRACTICE:
  - One tool = one responsibility
  - Tools should be stateless and pure where possible
  - Raise typed exceptions, never return error strings
  - Keep docstrings clear — Strands passes them to the model as tool descriptions
"""

from strands import tool


@tool
def fetch_data_from_source(query: str) -> str:
    """
    Fetches raw data relevant to the query from the primary data source.
    Returns a JSON string of results, or raises if source is unavailable.
    """
    # TODO: replace with real DB / API call
    return f'{{"status": "ok", "data": "sample data for: {query}"}}'


@tool
def check_data_sufficiency(data: str) -> bool:
    """
    Returns True if the data is sufficient to continue processing.
    Returns False if the pipeline should halt early.
    """
    # TODO: replace with real sufficiency logic
    return len(data) > 10


@tool
def fetch_activity_logs(entity_id: str) -> str:
    """
    Retrieves activity logs for a given entity ID.
    Returns a JSON string of log entries.
    """
    # TODO: replace with real log store query
    return f'{{"entity_id": "{entity_id}", "logs": []}}'


@tool
def run_compliance_check(data: str) -> str:
    """
    Runs compliance rules against the provided data.
    Returns a JSON report with pass/fail status per rule.
    """
    # TODO: replace with real compliance engine call
    return '{"passed": true, "violations": []}'


@tool
def summarize_dataset(data: str) -> str:
    """
    Produces a concise summary of the provided dataset.
    Returns a plain-text summary string.
    """
    # TODO: replace with real summarisation logic
    return f"Summary of provided data: {data[:100]}..."


@tool
def verify_output(summary: str) -> str:
    """
    Verifies that the summary meets quality and accuracy standards.
    Returns a verification report as a JSON string.
    """
    # TODO: replace with real verification logic
    return '{"verified": true, "confidence": 0.95}'
