"""
FETCH -> VALIDATE -> CLEAN -> NORMALIZE -> ATTRIBUTE EXTRACTION -> UPSERT ->
TRIGGER EXISTING AI PIPELINE -> AUTOMATIC BATCH SETTLEMENT (spec section 4/26-29).

This module owns the entire source-connection sync lifecycle (full and
incremental) but deliberately contains NONE of the AI logic itself: every
created/changed CPSEMaterial is handed to the exact same `ai_analysis`
Celery task (app.workers.tasks) the rest of the application already uses.
SBERT, pgvector, XGBoost, conflict detection and common-code generation are
untouched and never reimplemented here.

Once every material in a batch has been analyzed once, one settling pass
(app.workers.tasks.settle_batch, run as a Celery chord callback - see
trigger_batch_settlement below) re-analyzes the same batch so materials
that matched each other but were processed before their counterpart had an
embedding converge to the correct shared mapping automatically, without a
human needing to trigger the manual /harmonization/scan rescan.

trigger_batch_settlement is exported (no leading underscore) so
app.services.csv_import_service can hand its own newly-imported batch to
the exact same settlement mechanism - the demo-only CSV path converges
materials the same way a real source-connector sync does, never a
separate/duplicated implementation.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.connectors.base import CanonicalMaterialRecord, CanonicalRecordPage
from app.connectors.exceptions import ConnectorError
from app.connectors.registry import build_connector
from app.models.enums import SynchronizationStatus
from app.models.material import CPSEMaterial
from app.models.source_connection import SourceConnection, SyncHistory
from app.services import material_ingestion
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _dispatch_batch_chord(material_ids: list[str]):
    """
    Fires the whole batch's analysis in parallel (a Celery `group`) with a
    single settling pass as the `chord` callback, which Celery's own result
    backend only invokes once every task in the group has actually
    finished - not a fixed delay, a real completion signal. This is what
    lets a burst of newly-synced, mutually-matching materials (e.g. the same
    physical item synced from two CPSEs moments apart in the same batch)
    converge to its final common-material mapping automatically, without a
    human needing to trigger a manual rescan (spec section 28).

    Isolated in its own function so tests can monkeypatch exactly this
    integration point to simulate "no broker reachable", the same way the
    rest of the app's `.delay()` call sites are already isolated for that
    purpose.
    """
    from celery import chord

    from app.workers.tasks import ai_analysis, settle_batch

    return chord(ai_analysis.s(mid) for mid in material_ids)(settle_batch.s(material_ids))


def _settle_inline(db: Session, material_ids: list[uuid.UUID]) -> None:
    """No-broker fallback (isolated test/dev setup): runs every material's
    analysis synchronously, then a second pass over the same set to settle
    it - the same two-phase shape the chord above gives you when a broker
    IS reachable, just executed inline instead of via Celery."""
    from app.ai.analyzer import analyze_material

    for material_id in material_ids:
        analyze_material(db, material_id)
    for material_id in material_ids:
        analyze_material(db, material_id)


def trigger_batch_settlement(db: Session, to_analyze: list[uuid.UUID], *, wait: bool = False) -> None:
    if not to_analyze:
        return
    material_ids = [str(mid) for mid in to_analyze]
    try:
        async_result = _dispatch_batch_chord(material_ids)
        if wait:
            from app.core.config import settings

            async_result.get(timeout=settings.SOURCE_SYNC_SETTLE_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001 - no broker reachable, or the wait above timed out
        _settle_inline(db, to_analyze)


def _upsert_material(
    db: Session, connection: SourceConnection, batch: SyncHistory, record: CanonicalMaterialRecord
) -> tuple[str, CPSEMaterial | None]:
    """Thin wrapper over the shared upsert core (app.services.material_ingestion),
    which app.services.csv_import_service also calls for the demo-only CSV
    import path - the two ingestion mechanisms share one upsert
    implementation and can never diverge in idempotency/governance behavior."""
    return material_ingestion.upsert_cpse_material(
        db,
        cpse_id=connection.cpse_id,
        record=record,
        actor_name=connection.connection_name,
        actor_type="SYSTEM",
        source_connection_id=connection.id,
        sync_history_id=batch.id,
        log_details_extra={"connection": connection.connection_name},
    )


def _run_sync(
    db: Session, connection: SourceConnection, sync_type: str, fetch_page, *, wait_for_settlement: bool = False
) -> SyncHistory:
    started = datetime.now(timezone.utc)
    batch = SyncHistory(source_connection_id=connection.id, started_at=started, status="RUNNING", sync_type=sync_type)
    db.add(batch)
    connection.last_sync_started_at = started
    connection.last_sync_status = "RUNNING"
    connection.cpse.synchronization_status = SynchronizationStatus.SYNCING.value
    db.commit()
    db.refresh(batch)

    counts = {"created": 0, "updated": 0, "skipped": 0, "failed": 0}
    discovered = 0
    to_analyze: list[uuid.UUID] = []
    newest_cursor: datetime | None = None

    from app.core.config import settings

    try:
        page = 1
        while page <= settings.SOURCE_SYNC_MAX_PAGES_PER_RUN:
            record_page: CanonicalRecordPage = fetch_page(page)
            discovered += len(record_page.items)
            for record in record_page.items:
                try:
                    outcome, material = _upsert_material(db, connection, batch, record)
                    counts[outcome] += 1
                    if material is not None:
                        to_analyze.append(material.id)
                    if record.source_updated_at and (newest_cursor is None or record.source_updated_at > newest_cursor):
                        newest_cursor = record.source_updated_at
                except Exception as exc:  # noqa: BLE001 - one bad record must not fail the whole batch
                    db.rollback()
                    counts["failed"] += 1
                    logger.warning("Material upsert failed for %s: %s", record.original_material_code, exc)
            if not record_page.has_more:
                break
            page += 1

        completed = datetime.now(timezone.utc)
        batch.status = "SUCCESS" if counts["failed"] == 0 else "PARTIAL"
        batch.completed_at = completed
        batch.records_discovered = discovered
        batch.records_inserted = counts["created"]
        batch.records_updated = counts["updated"]
        batch.records_skipped = counts["skipped"]
        batch.records_failed = counts["failed"]
        if newest_cursor is not None:
            batch.last_successful_cursor = newest_cursor.isoformat()

        connection.last_error = None
        connection.last_sync_status = batch.status
        connection.cpse.last_sync_at = completed
        connection.cpse.synchronization_status = batch.status
        # Only advance the incremental cursor when NOTHING failed - a
        # partial failure must not let the next incremental sync skip past
        # the records that failed this time (spec section 27).
        if counts["failed"] == 0 and newest_cursor is not None:
            connection.last_synced_cursor = newest_cursor.isoformat()
            connection.last_successful_sync = completed
        db.commit()

        log_action(
            db,
            action=f"{sync_type}_SYNC_COMPLETED",
            entity_type="source_connection",
            entity_id=connection.id,
            actor_name=connection.connection_name,
            actor_type="SYSTEM",
            details={"batch_id": str(batch.id), "discovered": discovered, **counts},
        )
    except ConnectorError as exc:
        db.rollback()
        completed = datetime.now(timezone.utc)
        batch.status = "FAILED"
        batch.completed_at = completed
        batch.error_message = str(exc)
        batch.records_discovered = discovered
        batch.records_inserted = counts["created"]
        batch.records_updated = counts["updated"]
        batch.records_skipped = counts["skipped"]
        batch.records_failed = counts["failed"]

        connection.last_sync_status = "FAILED"
        connection.last_error = str(exc)
        connection.cpse.synchronization_status = SynchronizationStatus.FAILED.value
        # Cursor is NOT advanced and no existing material is touched -
        # previous data survives untouched; the next sync retries from the
        # same starting point (spec section 30).
        db.commit()

        log_action(
            db,
            action=f"{sync_type}_SYNC_FAILED",
            entity_type="source_connection",
            entity_id=connection.id,
            actor_name=connection.connection_name,
            actor_type="SYSTEM",
            reason=str(exc),
        )

    trigger_batch_settlement(db, to_analyze, wait=wait_for_settlement)

    return batch


def list_due_connections(db: Session) -> list[SourceConnection]:
    now = datetime.now(timezone.utc)
    due: list[SourceConnection] = []
    connections = db.query(SourceConnection).filter(SourceConnection.enabled.is_(True)).all()
    for connection in connections:
        if connection.last_sync_started_at is None:
            due.append(connection)
            continue
        elapsed = (now - connection.last_sync_started_at).total_seconds()
        if elapsed >= connection.sync_interval_seconds:
            due.append(connection)
    return due


def run_full_sync(db: Session, connection: SourceConnection, *, wait_for_settlement: bool = False) -> SyncHistory:
    """
    `wait_for_settlement` blocks until this batch's post-sync harmonization
    pass has actually finished (real completion tracking via the Celery
    result backend - see trigger_batch_settlement - not a fixed delay).
    Off by default so a caller triggering a sync (e.g. an API request or
    the scheduled Beat tick) is never blocked on AI processing; a script
    that wants every batch fully settled before starting the next one
    (e.g. app.demo_seed, so a demo converges deterministically without
    depending on inter-batch timing) can opt in.
    """
    from app.core.config import settings

    connector = build_connector(connection)
    try:
        return _run_sync(
            db, connection, "FULL",
            lambda page: connector.fetch_all(page=page, page_size=settings.SOURCE_SYNC_DEFAULT_PAGE_SIZE),
            wait_for_settlement=wait_for_settlement,
        )
    finally:
        connector.close()


def run_incremental_sync(db: Session, connection: SourceConnection, *, wait_for_settlement: bool = False) -> SyncHistory:
    from app.core.config import settings

    connector = build_connector(connection)
    since = None
    if connection.last_synced_cursor:
        since = datetime.fromisoformat(connection.last_synced_cursor)
    since = since or _EPOCH
    try:
        return _run_sync(
            db, connection, "INCREMENTAL",
            lambda page: connector.fetch_changed_since(since, page=page, page_size=settings.SOURCE_SYNC_DEFAULT_PAGE_SIZE),
            wait_for_settlement=wait_for_settlement,
        )
    finally:
        connector.close()
