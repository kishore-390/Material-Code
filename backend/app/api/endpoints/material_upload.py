"""
Company self-service material master upload (real production data).

This is the OTHER half of app.services.csv_import_service - unlike
app.api.endpoints.demo_import (DEMO ONLY, admin-restricted, any onboarded
CPSE), this endpoint lets an authorized user belonging to a specific CPSE
upload their OWN company's real material master as CSV or Excel (.xlsx),
strictly scoped to their own CPSE. Every row is marked is_demo_data=False
and passes through the exact same canonical ingestion + AI pipeline every
other path (including the secure read-only database connectors) uses -
there is no separate upload-specific matching/scoring logic here.

A user with no cpse_id (a central/ADMIN account) may instead upload on
behalf of a specific CPSE by naming it explicitly - the same dual-audience
pattern app.api.endpoints.demo_import already uses for CPSE selection.
"""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.cpse import CPSE
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

router = APIRouter(prefix="/materials/upload", tags=["Material Upload"])

# VIEWER is deliberately excluded - a read-only account should not be able
# to introduce new material rows for its company.
_ALLOWED_ROLES = (RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value, RoleName.REVIEWER.value)

MAX_FILE_SIZE_BYTES = svc.MAX_FILE_SIZE_BYTES
_ALLOWED_EXTENSIONS = (".csv", ".xlsx")


def _resolve_upload_cpse(current_user: User, requested_cpse_id: Optional[uuid.UUID], db: Session) -> CPSE:
    """
    A company-scoped user (cpse_id set at registration) can only ever
    upload for their own CPSE - any requested_cpse_id is ignored if it
    matches, rejected outright if it doesn't. A central/ADMIN user with no
    CPSE affiliation must explicitly name which CPSE they are uploading on
    behalf of.
    """
    if current_user.cpse_id is not None:
        if requested_cpse_id is not None and requested_cpse_id != current_user.cpse_id:
            raise HTTPException(status_code=403, detail="You can only upload materials for your own company.")
        cpse = db.query(CPSE).filter(CPSE.id == current_user.cpse_id).first()
    else:
        if requested_cpse_id is None:
            raise HTTPException(
                status_code=422,
                detail="cpse_id is required when uploading as a central/admin user on behalf of a CPSE.",
            )
        cpse = db.query(CPSE).filter(CPSE.id == requested_cpse_id).first()
    if cpse is None:
        raise HTTPException(status_code=404, detail="CPSE not found.")
    return cpse


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    if not file.filename or not file.filename.lower().endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=422, detail="Only .csv or .xlsx files are accepted.")
    # Display/audit only - never used to build a filesystem path, so path
    # traversal in the client-supplied name has nothing to act on.
    filename = os.path.basename(file.filename)
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB upload limit.")
    return filename, raw_bytes


def _issue(row: "svc.RowResult") -> CsvRowIssue:
    return CsvRowIssue(
        row_number=row.row_number,
        errors=row.errors,
        cpse_code=row.raw.get("cpse_code"),
        original_material_code=row.raw.get("original_material_code"),
    )


@router.post("/validate", response_model=CsvValidationResponse)
async def validate_upload(
    file: UploadFile,
    cpse_id: Optional[uuid.UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ALLOWED_ROLES)),
):
    """Preview-only: parses and fully validates the file without writing
    anything to the database."""
    cpse = _resolve_upload_cpse(current_user, cpse_id, db)
    filename, raw_bytes = await _read_upload(file)
    try:
        result = svc.validate_material_file(
            db, filename=filename, raw_bytes=raw_bytes, is_demo_data=False, allowed_cpse_ids={cpse.id}
        )
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
async def confirm_upload(
    file: UploadFile,
    cpse_id: Optional[uuid.UUID] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ALLOWED_ROLES)),
):
    """
    Re-validates the uploaded file (never trusts a client-held validation
    token - the file is the source of truth) and, only for rows that pass
    every check, imports through the canonical ingestion pipeline as REAL
    (is_demo_data=False) material data for the resolved CPSE. Invalid rows
    are NEVER inserted, even partially.
    """
    cpse = _resolve_upload_cpse(current_user, cpse_id, db)
    filename, raw_bytes = await _read_upload(file)
    try:
        validation = svc.validate_material_file(
            db, filename=filename, raw_bytes=raw_bytes, is_demo_data=False, allowed_cpse_ids={cpse.id}
        )
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
        is_demo_data=False, source_label="COMPANY_MATERIAL_UPLOAD",
        batch_entity_type="material_upload_batch", batch_action="COMPANY_MATERIAL_UPLOAD_COMPLETED",
        row_created_action="MATERIAL_UPLOADED_CREATED", row_updated_action="MATERIAL_UPLOADED_UPDATED",
        batch_details_extra={"cpse_id": str(cpse.id), "cpse_code": cpse.code},
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
def upload_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """A company-scoped user only ever sees their own company's upload
    history; a central/ADMIN user (no cpse_id) sees every company's."""
    query = db.query(AuditLog).filter(
        AuditLog.entity_type == "material_upload_batch", AuditLog.action == "COMPANY_MATERIAL_UPLOAD_COMPLETED"
    )
    entries = query.order_by(AuditLog.created_at.desc()).limit(200).all()

    if current_user.cpse_id is not None:
        own_code = current_user.cpse.code.upper()
        entries = [e for e in entries if (e.details or {}).get("cpse_code", "").upper() == own_code]

    entries = entries[:100]

    items = [
        CsvImportHistoryItem(
            batch_id=entry.entity_id or uuid.uuid4(),
            filename=(entry.details or {}).get("filename", "unknown"),
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
    return CsvImportHistoryResponse(items=items, total=len(items))


@router.get("/template", response_class=PlainTextResponse)
def upload_template(current_user: User = Depends(get_current_user)):
    """A blank column-header template (+ one example row) for a company's
    own material master export - see app.services.csv_import_service.build_upload_template_csv."""
    return PlainTextResponse(
        content=svc.build_upload_template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=material_upload_template.csv"},
    )
