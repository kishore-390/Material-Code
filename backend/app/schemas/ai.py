import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.material import MaterialOut


class CandidateOut(BaseModel):
    material: MaterialOut
    final_score: float
    description_score: float
    specification_score: float
    category_score: float
    uom_score: float
    image_score: float
    attribute_score: float


class AIAnalysisOut(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    final_score: float
    description_score: float
    specification_score: float
    category_score: float
    uom_score: float
    image_score: float
    attribute_score: float
    ml_probability: Optional[float] = None
    ml_status: Optional[str] = None
    decision: str
    reason_text: Optional[str] = None
    recommended_common_code: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    technical_conflict: bool = False
    conflict_reason: Optional[str] = None
    best_candidate: Optional[MaterialOut] = None
    candidates: list[CandidateOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyzeTriggerResponse(BaseModel):
    material_id: uuid.UUID
    task_id: Optional[str] = None
    status: str
