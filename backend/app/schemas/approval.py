import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.material import MaterialOut


class FieldComparison(BaseModel):
    field: str
    original_value: Optional[str] = None
    candidate_value: Optional[str] = None
    match: str  # "SAME" | "SIMILAR" | "DIFFERENT"


class ApprovalActionOut(BaseModel):
    id: uuid.UUID
    action: str
    actor_name: str
    remarks: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalRequestOut(BaseModel):
    id: uuid.UUID
    harmonization_request_id: uuid.UUID
    material: MaterialOut
    candidate: Optional[MaterialOut] = None
    ai_score: Optional[float] = None
    status: str
    reason: Optional[str] = None
    created_at: datetime
    actions: list[ApprovalActionOut] = []

    class Config:
        from_attributes = True


class ApprovalDetailOut(ApprovalRequestOut):
    comparison: list[FieldComparison] = []


class ApprovalActionRequest(BaseModel):
    action: str  # APPROVE | REJECT | REQUEST_MORE_INFO | MERGE | NOT_SAME_MATERIAL
    remarks: Optional[str] = None
