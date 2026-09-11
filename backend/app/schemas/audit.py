import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_name: str
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    reason: Optional[str] = None
    ai_model_version: Optional[str] = None
    confidence: Optional[float] = None
    details: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
