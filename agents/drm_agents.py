"""
agents/drm_agents.py
─────────────────────
Sub-agents owned by the Data Request Manager super agent.

Each agent:
  - Has a focused system prompt describing exactly its role
  - Gets only the tools it needs (principle of least privilege)
  - Raises typed exceptions for known failure modes
"""

from agents.base_agent import BaseAgent
from tools.data_tools import (
    fetch_data_from_source,
    check_data_sufficiency,
    fetch_activity_logs,
    run_compliance_check,
)
from utils.exceptions import InsufficientDataError
from utils.logger import logger


class DataAnalystAgent(BaseAgent):
    """
    First in the DRM pipeline.
    Fetches and evaluates data. Raises InsufficientDataError
    if the data cannot support further processing — this is the
    only early-exit point in the entire pipeline.
    """

    SYSTEM_PROMPT = """
    You are a Data Analyst Agent.

    Your responsibilities:
    1. Use fetch_data_from_source to retrieve data relevant to the query.
    2. Use check_data_sufficiency to evaluate whether the data is adequate.
    3. If data is sufficient, return a structured summary of what you found.
    4. If data is NOT sufficient, clearly state: "INSUFFICIENT DATA: <reason>"

    Be concise and factual. Do not make assumptions about missing data.
    """

    TOOLS = [fetch_data_from_source, check_data_sufficiency]

    def run(self, query: str) -> str:
        result = super().run(query)

        # Detect early-exit signal from the model's response
        if result.strip().upper().startswith("INSUFFICIENT DATA"):
            logger.warning(f"DataAnalystAgent | early exit triggered: {result}")
            raise InsufficientDataError(result)

        return result


class ActivityMonitorAgent(BaseAgent):
    """
    Second in the DRM pipeline.
    Receives the data analyst's output and monitors
    activity patterns related to the request.
    """

    SYSTEM_PROMPT = """
    You are an Activity Monitor Agent.

    You receive a data summary from the Data Analyst.
    Your responsibilities:
    1. Use fetch_activity_logs to retrieve relevant activity records.
    2. Identify any anomalies, trends, or patterns of concern.
    3. Return a structured activity report.

    Be specific about what activity you observed and any flags raised.
    """

    TOOLS = [fetch_activity_logs]


class ComplianceAgent(BaseAgent):
    """
    Third in the DRM pipeline.
    Receives combined data and activity output, runs compliance checks.
    """

    SYSTEM_PROMPT = """
    You are a Compliance Agent.

    You receive a data and activity report.
    Your responsibilities:
    1. Use run_compliance_check to evaluate the data against compliance rules.
    2. Identify any violations or risks.
    3. Return a compliance status report with pass/fail per rule.

    Be precise. Flag every violation, even minor ones.
    """

    TOOLS = [run_compliance_check]
