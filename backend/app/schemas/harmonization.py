import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common_code import CommonMaterialCodeOut
from app.schemas.material import CommonCodeBrief, MaterialOut


class HarmonizationRequestCreate(BaseModel):
    material_id: uuid.UUID
    candidate_material_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class HarmonizationRequestOut(BaseModel):
    id: uuid.UUID
    material: MaterialOut
    candidate: Optional[MaterialOut] = None
    request_type: str
    status: str
    ai_score: Optional[float] = None
    common_code: Optional[CommonMaterialCodeOut] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HarmonizationActionRequest(BaseModel):
    remarks: Optional[str] = None


class ScanTriggerResponse(BaseModel):
    queued: int
    material_ids: list[uuid.UUID]
    mode: str  # "QUEUED" (Celery) or "PROCESSED_INLINE" (no broker reachable - ran synchronously)


class ScanStatusRequest(BaseModel):
    material_ids: list[uuid.UUID]


class ScanStatusItem(BaseModel):
    material_id: uuid.UUID
    material_code: str
    cpse_code: str
    description: str
    category: str
    material_status: str
    latest_decision: Optional[str] = None
    ai_confidence: Optional[float] = None
    technical_conflict: bool = False
    conflict_reason: Optional[str] = None
    best_candidate_material_code: Optional[str] = None
    best_candidate_cpse_code: Optional[str] = None
    common_code: Optional[CommonCodeBrief] = None


class ScanStatusResponse(BaseModel):
    total: int
    completed: int
    items: list[ScanStatusItem]
