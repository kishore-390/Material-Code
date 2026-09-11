"""
DEMO ONLY - Demo Data Import (spec section: SIH26099 demonstration
mechanism, see app.services.csv_import_service for the full rationale).

Production CPSE material data is synchronized automatically through secure
read-only database connectors (see app.api.endpoints.synchronization) - this
router exists solely so a live demonstration can populate the National
Material Master without a real CPSE database to connect to. Every row this
endpoint creates is marked is_demo_data=True and passes through the exact
same canonical ingestion + AI pipeline a real sync uses.
"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.csv_import import (
    CsvImportHistoryItem,
    CsvImportHistoryResponse,
    CsvImportResponse,
    CsvImportRowResult,
    CsvRowIssue,
    CsvValidationResponse,
)
from app.services import csv_import_service as svc

router = APIRouter(prefix="/demo-import", tags=["Demo Data Import"])

_ALLOWED_ROLES = (RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only .csv files are accepted.")
    # Display/audit only - never used to build a filesystem path, so path
    # traversal in the client-supplied name has nothing to act on.
    filename = os.path.basename(file.filename)
    raw_bytes = await file.read()
    if len(raw_bytes) > svc.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds the {svc.MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB demo import limit.")
    return filename, raw_bytes


def _issue(row: "svc.RowResult") -> CsvRowIssue:
    return CsvRowIssue(
        row_number=row.row_number,
        errors=row.errors,
        cpse_code=row.raw.get("cpse_code"),
        original_material_code=row.raw.get("original_material_code"),
    )


@router.post("/validate", response_model=CsvValidationResponse)
async def validate_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ALLOWED_ROLES)),
):
    """Preview-only: parses and fully validates the CSV without writing
    anything to the database, so the frontend can show valid/invalid counts
    and a row preview before the user confirms the import."""
    filename, raw_bytes = await _read_upload(file)
    try:
        result = svc.validate_material_file(db, filename=filename, raw_bytes=raw_bytes, is_demo_data=True)
    except svc.CsvImportError as exc:
        return CsvValidationResponse(
            filename=filename, total_rows=0, valid_count=0, invalid_count=0,
            is_importable=False, file_errors=[str(exc)], invalid_rows=[], preview=[],
        )

    return CsvValidationResponse(
        filename=result.filename,
        total_rows=result.total_rows,
        valid_count=len(result.valid_rows),
        invalid_count=len(result.invalid_rows),
        is_importable=result.is_importable,
        file_errors=result.file_errors,
        invalid_rows=[_issue(r) for r in result.invalid_rows],
        preview=[r.raw for r in result.valid_rows[: svc.PREVIEW_ROWS]],
    )


@router.post("/confirm", response_model=CsvImportResponse)
async def confirm_import(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ALLOWED_ROLES)),
):
    """
    Re-validates the uploaded file (never trusts a client-held validation
    token - the file is the source of truth) and, only for rows that pass
    every check, imports through the canonical ingestion pipeline. Invalid
    rows are NEVER inserted, even partially.
    """
    filename, raw_bytes = await _read_upload(file)
    try:
        validation = svc.validate_material_file(db, filename=filename, raw_bytes=raw_bytes, is_demo_data=True)
    except svc.CsvImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not validation.is_importable:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "No valid rows to import.",
                "file_errors": validation.file_errors,
                "invalid_rows": [_issue(r).model_dump() for r in validation.invalid_rows],
            },
        )

    summary = svc.import_valid_rows(
        db, validation, actor_id=current_user.id, actor_name=current_user.full_name,
        is_demo_data=True, source_label="DEMO_CSV_IMPORT",
        batch_entity_type="csv_import_batch", batch_action="CSV_DEMO_IMPORT_COMPLETED",
        row_created_action="MATERIAL_CSV_IMPORTED_CREATED", row_updated_action="MATERIAL_CSV_IMPORTED_UPDATED",
    )

    return CsvImportResponse(
        batch_id=summary.batch_id,
        filename=summary.filename,
        total_rows=summary.total_rows,
        valid_count=summary.valid_count,
        invalid_count=summary.invalid_count,
        created=summary.created,
        updated=summary.updated,
        skipped=summary.skipped,
        failed=summary.failed,
        invalid_rows=[_issue(r) for r in validation.invalid_rows],
        results=[
            CsvImportRowResult(
                row_number=r.row_number,
                cpse_code=r.cpse_code,
                original_material_code=r.original_material_code,
                outcome=r.outcome,
                common_material_code=r.common_material_code,
                mapping_type=r.mapping_type,
                decision_status=r.decision_status,
            )
            for r in summary.results
        ],
    )


@router.get("/history", response_model=CsvImportHistoryResponse)
def import_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AuditLog).filter(
        AuditLog.entity_type == "csv_import_batch", AuditLog.action == "CSV_DEMO_IMPORT_COMPLETED"
    )
    total = query.count()
    entries = query.order_by(AuditLog.created_at.desc()).limit(100).all()
    items = [
        CsvImportHistoryItem(
            batch_id=entry.entity_id or uuid.uuid4(),
            filename=(entry.details or {}).get("filename", "unknown.csv"),
            imported_at=entry.created_at,
            actor_name=entry.actor_name,
            total_rows=(entry.details or {}).get("total_rows", 0),
            valid_count=(entry.details or {}).get("valid_count", 0),
            invalid_count=(entry.details or {}).get("invalid_count", 0),
            created=(entry.details or {}).get("created", 0),
            updated=(entry.details or {}).get("updated", 0),
            skipped=(entry.details or {}).get("skipped", 0),
            failed=(entry.details or {}).get("failed", 0),
        )
        for entry in entries
    ]
    return CsvImportHistoryResponse(items=items, total=total)


@router.get("/sample-csv", response_class=PlainTextResponse)
def sample_csv(current_user: User = Depends(get_current_user)):
    """A ready-to-import demo CSV covering all 6 required decision
    categories (spec section 42) - see app.services.csv_import_service.build_sample_csv."""
    return PlainTextResponse(
        content=svc.build_sample_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=demo_material_import_sample.csv"},
    )
