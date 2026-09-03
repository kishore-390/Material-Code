import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common_code import CommonMaterialCodeOut
from app.schemas.material import MaterialOut


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
