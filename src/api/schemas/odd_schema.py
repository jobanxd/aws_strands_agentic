# src/api/schemas/odd_schema.py

from pydantic import BaseModel
from typing import Optional, List, Any


class ODDRequest(BaseModel):
    query: str


class ODDResponse(BaseModel):
    process_id: str
    status: str
    message: str


class ODDStatusResponse(BaseModel):
    process_id: str
    status: str                        # accepted | running | success | failed
    stopped_at: Optional[str] = None
    steps_completed: List[str] = []
    output: Optional[Any] = None
    error: Optional[str] = None