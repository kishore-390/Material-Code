import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CPSECreate(BaseModel):
    code: str
    name: str
    sector: Optional[str] = None


class CPSEOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    sector: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CPSEStats(CPSEOut):
    total_materials: int = 0
    harmonized_materials: int = 0
    pending_approvals: int = 0
    common_codes: int = 0
    duplicate_materials: int = 0
    harmonization_percentage: float = 0.0
