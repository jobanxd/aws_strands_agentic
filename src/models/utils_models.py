"""Model classes for Utils."""
from typing import Optional
from pydantic import BaseModel

class StepNotificationConfig(BaseModel):
    """Configuration for step status notifications."""

    step_number: int
    step_name: str
    start_message: str
    complete_message: str


class DocumentKeys(BaseModel):
    """Document keys for possible documents"""
    passport_key: Optional[str] = None
    generic_proof_of_id_key: Optional[str] = None
    employment_key: Optional[str] = None
    proof_of_address_key: Optional[str] = None


class DocumentProcessRequest(BaseModel):
    """Encapsulates the input context required to process a party document."""

    file_key: str
    party_id: str
    review_id: str
    document_type: str
