import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.material import CPSEMaterialOut


class CommonMaterialOut(BaseModel):
    id: uuid.UUID
    common_code: str
    standardized_description: str
    standardized_specification: Optional[str] = None
    material_type: str
    material_grade: Optional[str] = None
    dimensions: Optional[str] = None
    standardized_uom: str
    standard: Optional[str] = None
    function: Optional[str] = None
    criticality: str
    classification: str
    classification_path: Optional[list] = None
    status: str
    confidence: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CommonMaterialDetailOut(CommonMaterialOut):
    mapped_materials: list[CPSEMaterialOut] = []
    mapped_cpses: list[str] = []


class MappingOut(BaseModel):
    id: uuid.UUID
    common_material: CommonMaterialOut
    cpse_material: CPSEMaterialOut
    matched_against: Optional[CPSEMaterialOut] = None
    mapping_type: str
    decision_status: str
    confidence_score: Optional[float] = None
    evidence: Optional[dict] = None
    reason: Optional[str] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MappingListResponse(BaseModel):
    items: list[MappingOut]
    total: int
    page: int
    page_size: int
