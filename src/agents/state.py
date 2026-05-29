"""State for Agents Process"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.models.agent_models import (
    PartyInfo,
    ReviewInfo,
    SvoCExtract,
    ServiceLinkBundle,
    TextractData,
    DataAnalystOutput,

    EmploymentAnalysisResults,
    ActivityMonitorOutput,
)
from src.database.sqlite_manager import SQLiteDatabaseManager


@dataclass
class PipelineState:
    """
    State that will be utilized by the Agents during process
    """
    # ── Input ────────────────────────────────────────────────────────────────
    query: str
    db: SQLiteDatabaseManager = field(default_factory=SQLiteDatabaseManager)

    # ── Extracted by DataAnalystAgent ─────────────────────────────────────────
    party_id: Optional[str] = None

    # KYC
    kyc_party_info: Optional[List[PartyInfo]] = None        # all reviews
    latest_kyc_party_info: Optional[PartyInfo] = None       # most recent
    review_info: Optional[ReviewInfo] = None

    # SVoC
    svoc_data: Optional[List[SvoCExtract]] = None

    # ServiceLink
    servicelink_bundles: Optional[List[ServiceLinkBundle]] = None

    # Textract
    textract_data: Optional[TextractData] = None

    # Previous residence (edge case)
    previous_length_of_residence: Optional[str] = None

    # Final structured output from DataAnalystAgent
    data_analyst_output: Optional[DataAnalystOutput] = None

    # ── Extracted by ActivityMonitorAgent ─────────────────────────────────────
    active_svoc_data: Optional[List[SvoCExtract]] = None
    active_servicelink_bundles: Optional[List[ServiceLinkBundle]] = None

    
    account_summaries: Optional[List[Dict]] = None
    all_anomalies: Optional[List[Dict]] = None
    suspicious_activity_detected: bool = False
    final_cash_percentage: float = 0.0

    # Employment Analysis
    employment_analysis_results: Optional[EmploymentAnalysisResults] = None

    # Country Risk Analysis
    country_risk_analysis: Optional[Dict[str, Any]] = None


    activity_monitor_output: Optional[ActivityMonitorOutput] = None

    # ── Pipeline control ──────────────────────────────────────────────────────
    status: str = "pending"
    stopped_at: Optional[str] = None
    error_message: Optional[str] = None
    steps_completed: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def mark_step(self, step_name: str):
        """Record a completed step for audit trail."""
        self.steps_completed.append(step_name)

    def fail(self, stopped_at: str, message: str, status: str = "failed"):
        """Mark the pipeline as failed at a specific step."""
        self.status = status
        self.stopped_at = stopped_at
        self.error_message = message