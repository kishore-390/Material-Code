import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.material import CPSEMaterialOut


class CandidateOut(BaseModel):
    material: CPSEMaterialOut
    final_score: float
    description_score: float
    specification_score: float
    classification_score: float
    uom_score: float
    attribute_score: float
    grade_score: float
    dimension_score: float
    standard_score: float
    manufacturer_score: float
    function_score: float
    criticality_score: float


class AIAnalysisOut(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    final_score: float
    description_score: float
    specification_score: float
    classification_score: float
    uom_score: float
    attribute_score: float
    grade_score: float
    dimension_score: float
    standard_score: float
    manufacturer_score: float
    function_score: float
    criticality_score: float
    ml_probability: Optional[float] = None
    ml_status: Optional[str] = None
    decision: str
    reason_text: Optional[str] = None
    recommended_common_code: Optional[str] = None
    status: str
    failure_reason: Optional[str] = None
    technical_conflict: bool = False
    conflict_reason: Optional[str] = None
    best_candidate: Optional[CPSEMaterialOut] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyzeTriggerResponse(BaseModel):
    material_id: uuid.UUID
    task_id: Optional[str] = None
    status: str
