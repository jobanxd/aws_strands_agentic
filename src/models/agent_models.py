"""Models for agent outputs"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from src.models.data_models import (
    PartyInfo,
    ReviewInfo,
    TextractData,
    SvoCExtract,
    ServiceLinkBundle,
)

# ============================================================================
# DATA REQUEST MANAGER - Sub-Agent Models
# ============================================================================


class DataAnalystOutput(BaseModel):
    """Output from Data Analyst Agent - Raw data extraction"""

    party_info: PartyInfo
    review_info: ReviewInfo
    textract_data: TextractData
    svoc_data: List[SvoCExtract]
    servicelink_bundles: List[ServiceLinkBundle]
    previous_length_of_residence: Optional[str] = None
    summary: Optional[str] = None

class EmploymentAnalysisResults(BaseModel):
    """Output from the Employment Analysis"""

    employment_status: Optional[str] = None
    employment_status_reasoning: Optional[str] = None
    employer: Optional[str] = None
    employer_reasoning: Optional[str] = None
    employment_reason: Optional[str] = None
    employment_recommendation: Optional[str] = None

class ActivityMonitorOutput(BaseModel):
    """Output from Activity Monitor Agent - Transaction analysis"""

    party_id: str
    account_summaries: List[Dict[str, Any]]
    transaction_analysis: Dict[str, Any]
    employment_results: List[EmploymentAnalysisResults]
    cash_percentage: Optional[float] = None
    country_risk_analysis: Optional[Dict[str, Any]] = None


class IdentificationValidationResults(BaseModel):
    """Output from the identification validation check"""

    overall_matches: bool
    document_type: Optional[str] = None
    is_full_name_matching: bool
    is_dob_matching: Optional[bool] = None
    is_gender_matching: Optional[bool] = None
    is_country_of_birth_matching: Optional[bool] = None
    is_country_of_citizenship_matching: Optional[bool] = None
    analysis: str
    summary: str
    reason_for_unmatch: Optional[str] = None
    recommendation_for_unmatch: Optional[str] = None


class EmploymentValidationResults(BaseModel):
    """Output from the employment validation check"""

    overall_matches: bool
    document_type: Optional[str] = None
    is_full_name_matching: bool
    is_employment_status_matching: bool
    is_employer_matching: bool
    analysis: str
    summary: str
    reason_for_unmatch: Optional[str] = None
    recommendation_for_unmatch: Optional[str] = None


class AddressValidationResults(BaseModel):
    """Output from the address validation check"""

    overall_matches: bool
    document_type: Optional[str] = None
    is_full_name_matching: bool
    is_full_address_matching: bool
    analysis: str
    summary: str
    reason_for_unmatch: Optional[str] = None
    recommendation_for_unmatch: Optional[str] = None


class ComplianceCheckOutput(BaseModel):
    """Output from Compliance Agent - Data completeness verification"""

    party_id: str
    identification_validation: Optional[IdentificationValidationResults] = None
    employment_validation: Optional[EmploymentValidationResults] = None
    proof_of_address_validation: Optional[AddressValidationResults] = None
    data_completeness_check: Dict[str, Any]
    ready_for_odd_validation: bool


class DataRequestManagerOutput(BaseModel):
    """Aggregated output from Data Request Manager Super Agent"""

    data_analyst: DataAnalystOutput
    activity_monitor: ActivityMonitorOutput
    compliance_check: ComplianceCheckOutput
    overall_status: str
    manager_notes: str


# ============================================================================
# ODD VALIDATOR - Sub-Agent Models
# ============================================================================


class AnswerWithEvidence(BaseModel):
    """Per field contains these keys"""

    answer: Any
    status: str | None
    reason: Optional[str] = None
    evidence: Optional[str] = None


class KYCnetFormDataWithEvidence(BaseModel):
    """Fields under KYCnet Form Information"""

    type_of_customer: AnswerWithEvidence
    account_product: AnswerWithEvidence
    previous_review_risk_rating: AnswerWithEvidence
    title: AnswerWithEvidence
    full_name: AnswerWithEvidence
    first_name: AnswerWithEvidence
    middle_name: AnswerWithEvidence
    last_name: AnswerWithEvidence
    dob: AnswerWithEvidence
    gender: AnswerWithEvidence
    address: AnswerWithEvidence
    address_line_1: AnswerWithEvidence
    address_line_2: AnswerWithEvidence
    address_line_3: AnswerWithEvidence
    post_code: AnswerWithEvidence
    country_of_residence: AnswerWithEvidence
    country_of_birth: AnswerWithEvidence
    country_of_citizenship: AnswerWithEvidence
    length_of_residence: AnswerWithEvidence
    employment_status: AnswerWithEvidence
    occupation: AnswerWithEvidence
    employer_name: AnswerWithEvidence
    account_type_product: AnswerWithEvidence
    products_held: AnswerWithEvidence
    primary_account_identifier: AnswerWithEvidence
    proof_of_true_name_verification: AnswerWithEvidence
    proof_of_address_verification: AnswerWithEvidence


class KYCQuestionAnswersWithEvidence(BaseModel):
    """Fields under KYCnet Form Question and Answer"""

    cash_income_percentage: AnswerWithEvidence
    transacted_outside_safe_countries: AnswerWithEvidence
    high_risk_countries_info: AnswerWithEvidence
    very_high_risk_countries_info: AnswerWithEvidence
    prohibited_countries_info: AnswerWithEvidence
    source_funds_wealth_changed: AnswerWithEvidence
    suspicious_activity_detected: AnswerWithEvidence
    additional_information: AnswerWithEvidence
    escalation_required: AnswerWithEvidence


class KYCFullReview(BaseModel):
    """KYCnet Full Form"""

    kyc_form_data: KYCnetFormDataWithEvidence
    kyc_question_answers: KYCQuestionAnswersWithEvidence


class KYCnetOutputs(BaseModel):
    """Output from Data Summarizer Agent - Final KYC form"""

    party_id: str
    new_review_id: str
    kyc_form_data: KYCnetFormDataWithEvidence
    kyc_question_answers: KYCQuestionAnswersWithEvidence


class DataSummarizerOutput(BaseModel):
    """Output from Data Summarizer Agent - Frontend-ready final report (JSON structure for UI)"""

    party_id: Optional[str] = None
    old_review_id: Optional[str] = None
    new_review_id: Optional[str] = None
    report_data: Dict[str, Any]
    kycnet_output: KYCnetOutputs


class VerifierOutput(BaseModel):
    """Output from Verifier Agent - KYC form verification"""

    party_id: str
    is_validated: bool
    missing_fields: List[str]
    reason: str
    report_data: Dict[str, Any]


class AgentOutputParams(BaseModel):
    """Payload for storing an agent output record."""

    agent_name: str
    session_id: str
    process_id: str
    output: BaseModel
    summary: Optional[str] = None


class AgentFailureParams(BaseModel):
    """Payload for storing an agent failure record."""

    agent_name: str
    session_id: str
    process_id: str
    reason: str
    recommendation: str
    party_id: Optional[str] = None


class FinalReportParams(BaseModel):
    """Payload for storing a final report."""

    party_id: str
    new_review_id: str
    session_id: str
    process_id: str
    kyc_form_data: KYCnetFormDataWithEvidence
    kyc_question_answers: KYCQuestionAnswersWithEvidence
    overview_summary: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None


class FinalReportUpdateParams(BaseModel):
    """Payload for updating fields in the final_report table."""

    session_id: str
    review_id: str
    updates: Dict[str, str]
    modified_by: Optional[str] = None
    modified_at: Optional[str] = None


class AgentMessageParams(BaseModel):
    """Payload for storing an agent message."""

    session_id: str
    process_id: str
    payload: dict
    project_id: Optional[str] = None
    user_id: Optional[str] = None


class AgentTokenUsageParams(BaseModel):
    """Payload for storing agent token usage"""

    process_id: Optional[str] = None
    agent_name: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    response_preview: Optional[str] = None
