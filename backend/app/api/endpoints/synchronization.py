"""
Source connection CRUD + sync triggering (spec section 26/38). This is
deliberately NOT an "ERP management" page: it only ever shows connection
health/status and lets an ADMIN register a new CPSE's connector by naming
where its READ-ONLY credentials live as environment variables - it never
accepts, stores, or returns a secret value, and never lets anyone browse a
source database's contents beyond the material rows the sync itself imports.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.connectors.base import CANONICAL_FIELDS, REQUIRED_CANONICAL_FIELDS
from app.connectors.registry import build_connector
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.source_connection import SourceConnection, SyncHistory
from app.models.user import User
from app.schemas.source_connection import (
    SourceConnectionCreate,
    SourceConnectionOut,
    SourceConnectionUpdate,
    SyncHistoryListResponse,
    SyncTriggerResponse,
    TestConnectionResult,
)
from app.services.audit_service import log_action

router = APIRouter(prefix="/synchronization", tags=["Data Synchronization"])


def _get_or_404(db: Session, connection_id: uuid.UUID) -> SourceConnection:
    connection = db.query(SourceConnection).filter(SourceConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Source connection not found")
    return connection


@router.get("", response_model=list[SourceConnectionOut])
def list_connections(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(SourceConnection).order_by(SourceConnection.connection_name).all()


@router.post("", response_model=SourceConnectionOut, status_code=201)
def create_connection(
    payload: SourceConnectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    missing_required = [f for f in REQUIRED_CANONICAL_FIELDS if f not in payload.column_mapping]
    if missing_required:
        raise HTTPException(status_code=422, detail=f"column_mapping is missing required fields: {missing_required}")
    unknown_fields = [f for f in payload.column_mapping if f not in CANONICAL_FIELDS]
    if unknown_fields:
        raise HTTPException(status_code=422, detail=f"column_mapping has unrecognized fields: {unknown_fields}")

    connection = SourceConnection(**payload.model_dump())
    db.add(connection)
    db.commit()
    db.refresh(connection)

    log_action(
        db,
        action="SOURCE_CONNECTION_CREATED",
        entity_type="source_connection",
        entity_id=connection.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"connection_name": connection.connection_name, "database_type": connection.database_type},
    )
    return connection


@router.patch("/{connection_id}", response_model=SourceConnectionOut)
def update_connection(
    connection_id: uuid.UUID,
    payload: SourceConnectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    connection = _get_or_404(db, connection_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(connection, field, value)
    db.commit()
    db.refresh(connection)
    log_action(
        db,
        action="SOURCE_CONNECTION_UPDATED",
        entity_type="source_connection",
        entity_id=connection.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details=payload.model_dump(exclude_unset=True, exclude={"secret_reference"}),
    )
    return connection


@router.delete("/{connection_id}", status_code=204)
def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    connection = _get_or_404(db, connection_id)
    db.delete(connection)
    db.commit()


@router.post("/{connection_id}/test-connection", response_model=TestConnectionResult)
def test_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    connection = _get_or_404(db, connection_id)
    try:
        connector = build_connector(connection)
    except (ValueError,) as exc:
        return TestConnectionResult(connected=False, error=str(exc), checked_at=datetime.now(timezone.utc))

    try:
        result = connector.test_connection()
    finally:
        connector.close()

    log_action(
        db,
        action="SOURCE_CONNECTION_TEST" if result.connected else "SOURCE_CONNECTION_TEST_FAILED",
        entity_type="source_connection",
        entity_id=connection.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"connected": result.connected, "error": result.error},
    )
    return TestConnectionResult(
        connected=result.connected,
        database_version=result.database_version,
        latency_ms=result.latency_ms,
        error=result.error,
        checked_at=datetime.now(timezone.utc),
    )


def _trigger_sync(db: Session, connection: SourceConnection, sync_type: str) -> SyncTriggerResponse:
    from app.connectors import sync_engine

    task = sync_engine.run_full_sync if sync_type == "FULL" else sync_engine.run_incremental_sync
    mode = "QUEUED"
    task_id = None
    batch = None
    try:
        from app.workers.tasks import run_source_full_sync, run_source_incremental_sync

        celery_task = run_source_full_sync if sync_type == "FULL" else run_source_incremental_sync
        result = celery_task.delay(str(connection.id))
        task_id = result.id
    except Exception:  # noqa: BLE001 - no broker reachable (isolated test/dev setup)
        batch = task(db, connection)
        mode = "PROCESSED_INLINE"

    return SyncTriggerResponse(mode=mode, task_id=task_id, batch=batch)


@router.post("/{connection_id}/sync", response_model=SyncTriggerResponse)
def sync_now(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    """Incremental sync - only materials changed since the last successful cursor."""
    connection = _get_or_404(db, connection_id)
    return _trigger_sync(db, connection, "INCREMENTAL")


@router.post("/{connection_id}/full-sync", response_model=SyncTriggerResponse)
def full_sync(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)),
):
    """Full table re-pull, paginated through every record the source has."""
    connection = _get_or_404(db, connection_id)
    return _trigger_sync(db, connection, "FULL")


@router.get("/{connection_id}/sync-history", response_model=SyncHistoryListResponse)
def sync_history(
    connection_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    connection = _get_or_404(db, connection_id)
    query = db.query(SyncHistory).filter(SyncHistory.source_connection_id == connection.id)
    total = query.count()
    items = query.order_by(SyncHistory.started_at.desc()).limit(limit).all()
    return SyncHistoryListResponse(items=items, total=total)
