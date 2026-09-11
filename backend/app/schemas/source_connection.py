import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.user import CPSEBrief


class SourceConnectionCreate(BaseModel):
    cpse_id: uuid.UUID
    connection_name: str
    database_type: str  # POSTGRESQL | MYSQL | ORACLE | SQLSERVER
    host: str
    port: int
    database_name: str
    username_reference: str
    secret_reference: str
    ssl_enabled: bool = True
    table_name: str
    column_mapping: dict
    cursor_column: Optional[str] = None
    sync_interval_seconds: int = 300
    enabled: bool = True


class SourceConnectionUpdate(BaseModel):
    connection_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username_reference: Optional[str] = None
    secret_reference: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    table_name: Optional[str] = None
    column_mapping: Optional[dict] = None
    cursor_column: Optional[str] = None
    sync_interval_seconds: Optional[int] = None
    enabled: Optional[bool] = None


class SourceConnectionOut(BaseModel):
    """
    Never includes a secret value - only the environment-variable NAME the
    credential is expected to live in (spec section F: 'database credentials
    must never be exposed to the frontend').
    """

    id: uuid.UUID
    cpse: CPSEBrief
    connection_name: str
    database_type: str
    host: str
    port: int
    database_name: str
    username_reference: str
    secret_reference: str
    ssl_enabled: bool
    read_only: bool
    table_name: str
    column_mapping: dict
    cursor_column: Optional[str] = None
    enabled: bool
    sync_interval_seconds: int
    last_sync_started_at: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_error: Optional[str] = None
    is_demo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncHistoryOut(BaseModel):
    id: uuid.UUID
    source_connection_id: uuid.UUID
    sync_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_discovered: int
    records_inserted: int
    records_updated: int
    records_skipped: int
    records_failed: int
    last_successful_cursor: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SyncHistoryListResponse(BaseModel):
    items: list[SyncHistoryOut]
    total: int


class TestConnectionResult(BaseModel):
    connected: bool
    database_version: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime


class SyncTriggerResponse(BaseModel):
    mode: str  # "QUEUED" | "PROCESSED_INLINE"
    task_id: Optional[str] = None
    batch: Optional[SyncHistoryOut] = None
