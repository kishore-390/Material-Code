import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.material import MaterialAttributeOut
from app.schemas.user import CPSEBrief


class DuplicateCodeGroupOut(BaseModel):
    original_material_code: str
    cpses: list[str]
    materials_count: int


class DuplicateCodeListResponse(BaseModel):
    items: list[DuplicateCodeGroupOut]
    total: int
    total_duplicate_codes: int
    cpses_affected: int
    materials_affected: int


class DuplicateCodeMaterialOut(BaseModel):
    id: uuid.UUID
    original_material_code: str
    original_description: str
    technical_specification: Optional[str] = None
    classification: Optional[str] = None
    uom: str
    manufacturer: Optional[str] = None
    material_type: Optional[str] = None
    status: str
    cpse: CPSEBrief
    attributes: list[MaterialAttributeOut] = []
    updated_at: datetime

    class Config:
        from_attributes = True


class DuplicateCodePairOut(BaseModel):
    material_a_id: uuid.UUID
    material_b_id: uuid.UUID
    classification: str  # SAME_SOURCE_CODE | AI_TECHNICAL_EQUIVALENCE | TECHNICAL_CONFLICT


class DuplicateCodeCompareOut(BaseModel):
    original_material_code: str
    materials: list[DuplicateCodeMaterialOut]
    pairs: list[DuplicateCodePairOut]
