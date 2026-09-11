import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.user import CPSEBrief


class MaterialAttributeOut(BaseModel):
    id: uuid.UUID
    attr_key: str
    attr_value: str

    class Config:
        from_attributes = True


class CommonMaterialBrief(BaseModel):
    id: uuid.UUID
    common_code: str
    standardized_description: str
    status: str

    class Config:
        from_attributes = True


class CPSEMaterialOut(BaseModel):
    id: uuid.UUID
    original_material_code: str
    original_description: str
    normalized_description: Optional[str] = None
    material_type: Optional[str] = None
    material_grade: Optional[str] = None
    dimensions: Optional[str] = None
    technical_specification: Optional[str] = None
    normalized_specification: Optional[str] = None
    uom: str
    normalized_uom: Optional[str] = None
    manufacturer: Optional[str] = None
    standard: Optional[str] = None
    function: Optional[str] = None
    classification: Optional[str] = None
    classification_path: Optional[list] = None
    packaging: Optional[str] = None
    criticality: str
    quantity: Optional[float] = None
    is_active: bool
    status: str
    cpse: CPSEBrief
    source_created_at: Optional[datetime] = None
    source_updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CPSEMaterialDetailOut(CPSEMaterialOut):
    attributes: list[MaterialAttributeOut] = Field(default_factory=list)
    has_embedding: bool = False
    active_common_material: Optional[CommonMaterialBrief] = None


class MaterialListResponse(BaseModel):
    items: list[CPSEMaterialOut]
    total: int
    page: int
    page_size: int
