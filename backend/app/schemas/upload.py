import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.user import CPSEBrief


class UploaderBrief(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str

    class Config:
        from_attributes = True


class UploadBatchOut(BaseModel):
    id: uuid.UUID
    cpse: CPSEBrief
    filename: str
    uploader: Optional[UploaderBrief] = None
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UploadBatchListResponse(BaseModel):
    items: list[UploadBatchOut]
    total: int
    page: int
    page_size: int
