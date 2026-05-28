"""Pydantic models for ODD Router."""

from typing import Optional
from pydantic import BaseModel


class MessageHistoryRequest(BaseModel):
    """Request schema for the message history endpoint."""

    process_id: str


class ODDReportRequest(BaseModel):
    """Request schema for the ODD report endpoint."""

    process_id: str


class ODDRequest(BaseModel):
    """Request schema for the ODD process endpoint."""

    party_id: str = None
    session_id: str = None
    project_id: str = None
    user_id: str = None


class FieldChangeRequest(BaseModel):
    """Schema representing a single field change within a feedback submission."""

    question_id: str  # e.g., "q1", "q2", "q3", "q4"
    field_name: str   # e.g., "response", "reason"
    original_value: str
    new_value: str


class SaveFeedbackRequest(BaseModel):
    """Request schema for saving reviewer feedback on an ODD report."""

    session_id: str
    review_id: str
    field_changes: list[FieldChangeRequest]
    modified_by: Optional[str] = None


class SaveFeedbackResponse(BaseModel):
    """Response schema for the save feedback endpoint."""

    success: bool
    message: str
    records_inserted: int
    session_id: str
    review_id: str


class ApproveModificationRequest(BaseModel):
    """Request schema for approving pending field modifications."""

    session_id: str
    review_id: str


class ApproveModificationResponse(BaseModel):
    """Response schema for the approve modification endpoint."""

    success: bool
    message: str
    updated_fields: list[str]
    session_id: str
    review_id: str
