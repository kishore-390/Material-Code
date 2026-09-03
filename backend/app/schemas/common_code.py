import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.material import MaterialOut


class CommonMaterialCodeOut(BaseModel):
    id: uuid.UUID
    code: str
    material_type: str
    category: str
    standard_description: str
    standard_specification: Optional[str] = None
    uom: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CommonMaterialCodeDetail(CommonMaterialCodeOut):
    linked_materials: list[MaterialOut] = []
    linked_cpses: list[str] = []
