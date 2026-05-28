"""Models for final report generation for FE"""

from __future__ import annotations
from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, Field

from models.data_models import (
    PartyInfo,
    ReviewInfo,
    TextractData,
    SvoCExtract,
    ServiceLinkBundle
)
from models.agent_models import (
    KYCQuestionAnswersWithEvidence,
    KYCnetFormDataWithEvidence,
    ComplianceCheckOutput,
)


# ----------------------------- Common building blocks ----------------------------- #
class LabelValueRow(BaseModel):
    """Label Value Row Model"""

    label: str
    value: Any


class LabelValueRowReasonEvidence(BaseModel):
    """Label Value Row Evidence Model"""
    label: str
    value: Any
    reason: Optional[str] = None
    evidence: Optional[EvidenceRef] = None


class LabelValueRowWithStatus(BaseModel):
    """
    Label Value Row with Status Model — used in information and questions cards.
    Carries its own status, reason, and per-field evidence references.
    """

    label: str
    value: Any
    status: Optional[Literal["Verified", "Mismatch", "Unverified", "Pending"]] = "Verified"
    reason: Optional[str] = None
    evidence: Optional[EvidenceRef] = None


class AIAnswerItemWithEvidence(BaseModel):
    """AI Answer Item with Evidence"""

    question: str
    answer: Any | str
    reason: str = ""
    evidence: Optional[EvidenceRef] = None


class EvidenceRef(BaseModel):
    """Evidence Reference Model"""

    primary: str
    supporting: List[str] = Field(default_factory=list)


class Card(BaseModel):
    """Card Model — evidence/source are now optional since rows carry their own evidence."""

    section: Optional[str] = None
    rows: List[
        Union[
            LabelValueRowWithStatus,
            LabelValueRowReasonEvidence,
            LabelValueRow,
            AIAnswerItemWithEvidence,
        ]
    ]


class DrilldownCard(BaseModel):
    """Card Model for drilldown — uses plain LabelValueRow only."""

    rows: List[LabelValueRow]


class SectionWithCards(BaseModel):
    """Section with cards model"""

    title: str
    cards: List[Card]


class Overview(BaseModel):
    """Overview model"""

    title: str
    bullets: List[str] = Field(default_factory=list)


# ----------------------------- KYCNet sections ----------------------------- #
class KYCNetDrilldown(BaseModel):
    """KYCNet Drill Down Frontend Model — uses DrilldownCard (plain rows, no status)."""

    title: str
    cards: List[DrilldownCard]


class KYCNetInformation(BaseModel):
    """KYCNet Information Frontend Model — uses Card with LabelValueRowWithStatus rows."""

    title: str
    cards: List[Card]


class KYCNetQuestions(BaseModel):
    """KYCNet Questions Frontend Model — uses Card with LabelValueRowWithStatus rows."""

    title: str
    cards: List[Card]


class KYCNet(BaseModel):
    """KYCNet Frontend Model combine"""

    drilldown: KYCNetDrilldown
    information: KYCNetInformation
    questions: KYCNetQuestions


# ----------------------------- LLM based responses ----------------------------- #
class AIAnswerItem(BaseModel):
    """AI Answer Item Model"""

    question: str
    answer: Any | str
    reason: str = ""


class LLMBasedResponses(BaseModel):
    """LLM Based Responses Model"""

    title: str
    items: List[AIAnswerItem]


# ----------------------------- Evidence documents ----------------------------- #
class PreviewImage(BaseModel):
    """Preview Image Model for Frontend"""

    type: Literal["image"]
    url: str
    alt: str


class PreviewTable(BaseModel):
    """Preview Table Model"""

    type: Literal["table"]
    content: list[dict[str, Any]]
    alt: str


Preview = Union[PreviewImage, PreviewTable]


class EvidenceCheck(BaseModel):
    """Evidence Check Model"""

    field: str
    document: Any
    profile: str
    match: bool


class EvidenceDetails(BaseModel):
    """Evidence Details Model"""

    title: str
    subtitle: str
    reason: Optional[str] = None


class EvidenceDocument(BaseModel):
    """Evidence Document Model"""

    key: str
    label: str
    details: EvidenceDetails
    preview: Preview
    cash_calculation: Optional[dict] = None
    checks: Optional[List[EvidenceCheck]] = None
    document_source: Optional[str] = None
    data_source: Optional[str] = None


class Evidence(BaseModel):
    """Evidence Model"""

    documents: List[EvidenceDocument]


# ----------------------------- Root report model ----------------------------- #
class FinalReportInput(BaseModel):
    """Model class For FinalReport Input"""

    svoc: Optional[List[SvoCExtract]]
    servicelink: List[ServiceLinkBundle]
    party_info: Optional[PartyInfo]
    review_info: Optional[ReviewInfo]
    kyc_qna: Optional[KYCQuestionAnswersWithEvidence]
    textract_data: Optional[TextractData]
    kyc_form_data: Optional[KYCnetFormDataWithEvidence]
    new_review_id: Optional[str]
    avg_cash_calc: Optional[float] = 0.00
    ca_output: Optional[ComplianceCheckOutput] = None


class FinalReport(BaseModel):
    """Model class For FinalReport Output"""

    report_title: str
    new_review_id: str
    overview: Overview
    next_steps: List[str] = Field(default_factory=list)
    kycnet: KYCNet
    llm_based_responses: LLMBasedResponses
    evidence: Evidence
