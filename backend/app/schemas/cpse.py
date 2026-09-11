import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CPSECreate(BaseModel):
    code: str
    name: str
    sector: Optional[str] = None
    description: Optional[str] = None


class CPSEUpdate(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None


class CPSEStatusUpdate(BaseModel):
    is_active: bool


class CPSEOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    sector: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool
    last_sync_at: Optional[datetime] = None
    synchronization_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CPSEStats(CPSEOut):
    total_materials: int = 0
    common_materials: int = 0
    unique_materials: int = 0
    duplicates: int = 0
    near_duplicates: int = 0
    functional_equivalents: int = 0
    pending_mappings: int = 0
    legacy_codes: int = 0
