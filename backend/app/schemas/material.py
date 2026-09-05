import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.user import CPSEBrief


class MaterialAttributeIn(BaseModel):
    attr_key: str
    attr_value: str


class MaterialAttributeOut(MaterialAttributeIn):
    id: uuid.UUID

    class Config:
        from_attributes = True


class MaterialCreate(BaseModel):
    material_code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    specification: Optional[str] = None
    category: str
    uom: str
    cpse_code: str
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    material_type: Optional[str] = None
    attributes: dict[str, str] = Field(default_factory=dict)


class MaterialUpdate(BaseModel):
    description: Optional[str] = None
    specification: Optional[str] = None
    category: Optional[str] = None
    uom: Optional[str] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    material_type: Optional[str] = None


class CommonCodeBrief(BaseModel):
    id: uuid.UUID
    code: str
    standard_description: str
    status: str

    class Config:
        from_attributes = True


class MaterialOut(BaseModel):
    id: uuid.UUID
    material_code: str
    description: str
    normalized_description: Optional[str] = None
    specification: Optional[str] = None
    normalized_specification: Optional[str] = None
    category: str
    normalized_category: Optional[str] = None
    uom: str
    normalized_uom: Optional[str] = None
    manufacturer: Optional[str] = None
    brand: Optional[str] = None
    material_type: Optional[str] = None
    status: str
    image_url: Optional[str] = None
    cpse: CPSEBrief
    common_code: Optional[CommonCodeBrief] = None
    source_system: Optional[str] = None
    source_database: Optional[str] = None
    source_material_code: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaterialDetailOut(MaterialOut):
    attributes: list[MaterialAttributeOut] = Field(default_factory=list)
    has_embedding: bool = False


class MaterialListResponse(BaseModel):
    items: list[MaterialOut]
    total: int
    page: int
    page_size: int


class SimilarMaterialItem(BaseModel):
    material: MaterialOut
    similarity: float


class BulkValidationRow(BaseModel):
    row_number: int
    data: dict
    errors: list[str] = Field(default_factory=list)
    is_valid: bool


class BulkValidationResponse(BaseModel):
    batch_token: str
    upload_batch_id: Optional[uuid.UUID] = None
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[BulkValidationRow]


class BulkImportResponse(BaseModel):
    upload_batch_id: uuid.UUID
    status: str
    total_uploaded: int
    validation_errors: int
