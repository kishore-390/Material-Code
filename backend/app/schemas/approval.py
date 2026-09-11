import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.harmonization import MappingOut


class ApprovalActionOut(BaseModel):
    id: uuid.UUID
    action: str
    actor_name: str
    remarks: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalDetailOut(MappingOut):
    actions: list[ApprovalActionOut] = []


class ApprovalActionRequest(BaseModel):
    remarks: Optional[str] = None


class EditAndApproveRequest(BaseModel):
    remarks: Optional[str] = None
    standardized_description: Optional[str] = None
    standardized_specification: Optional[str] = None
    material_type: Optional[str] = None
    material_grade: Optional[str] = None
    dimensions: Optional[str] = None
    standardized_uom: Optional[str] = None
    standard: Optional[str] = None
    function: Optional[str] = None
    criticality: Optional[str] = None
    classification: Optional[str] = None
