import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CsvRowIssue(BaseModel):
    row_number: int
    errors: list[str]
    cpse_code: Optional[str] = None
    original_material_code: Optional[str] = None


class CsvValidationResponse(BaseModel):
    """Preview-only result of /demo-import/validate - nothing is written to
    the database by this call."""

    filename: str
    total_rows: int
    valid_count: int
    invalid_count: int
    is_importable: bool
    file_errors: list[str]
    invalid_rows: list[CsvRowIssue]
    preview: list[dict]


class CsvImportRowResult(BaseModel):
    row_number: int
    cpse_code: str
    original_material_code: str
    outcome: str  # created | updated | skipped | failed
    common_material_code: Optional[str] = None
    mapping_type: Optional[str] = None
    decision_status: Optional[str] = None


class CsvImportResponse(BaseModel):
    batch_id: uuid.UUID
    filename: str
    total_rows: int
    valid_count: int
    invalid_count: int
    created: int
    updated: int
    skipped: int
    failed: int
    invalid_rows: list[CsvRowIssue]
    results: list[CsvImportRowResult]


class CsvImportHistoryItem(BaseModel):
    batch_id: uuid.UUID
    filename: str
    imported_at: datetime
    actor_name: str
    total_rows: int
    valid_count: int
    invalid_count: int
    created: int
    updated: int
    skipped: int
    failed: int


class CsvImportHistoryResponse(BaseModel):
    items: list[CsvImportHistoryItem]
    total: int
