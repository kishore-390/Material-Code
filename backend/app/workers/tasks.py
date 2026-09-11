"""
Celery background jobs (spec section 40).

Every CPSE material synced from a source connection gets its AI analysis
queued here instead of blocking the sync request. `ai_analysis` is the
single entry point; it internally performs embedding generation, pgvector
similarity search, detailed scoring and the decision-engine step (see
app.ai.analyzer).
"""
import logging
import uuid

from app.ai import analyzer
from app.db.session import SessionLocal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.ai_analysis", bind=True, max_retries=2)
def ai_analysis(self, material_id: str) -> dict:
    db = SessionLocal()
    try:
        analysis = analyzer.analyze_material(db, uuid.UUID(material_id))
        return {
            "material_id": material_id,
            "decision": analysis.decision,
            "final_score": analysis.final_score,
            "status": analysis.status,
        }
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.bulk_ai_analysis")
def bulk_ai_analysis(material_ids: list[str]) -> dict:
    for material_id in material_ids:
        ai_analysis.delay(material_id)
    return {"queued": len(material_ids)}


@celery_app.task(name="app.workers.tasks.settle_batch", bind=True, max_retries=1)
def settle_batch(self, _group_results: list[dict], material_ids: list[str]) -> dict:
    """
    Chord callback (see app.connectors.sync_engine._dispatch_batch_chord) -
    Celery only invokes this once every `ai_analysis` task in the same sync
    batch has actually finished, via the result backend's own completion
    tracking (never a fixed delay). By then every material in the batch
    already has an embedding, so a second analysis pass over the same set
    can find candidates that didn't exist yet during each material's first,
    independent pass - settling a burst of newly-synced, mutually-matching
    materials into their final shared mapping automatically (spec section
    28). Re-analysis is idempotent and never reassigns an already-APPROVED
    mapping (app.ai.analyzer._handle_decision).

    `_group_results` (the list of each ai_analysis task's own return value)
    is unused - it exists only because Celery's chord calling convention
    passes the group's results as the callback's first argument.
    """
    db = SessionLocal()
    try:
        for material_id in material_ids:
            analyzer.analyze_material(db, uuid.UUID(material_id))
        return {"settled": len(material_ids)}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_source_full_sync", bind=True, max_retries=0)
def run_source_full_sync(self, source_connection_id: str) -> dict:
    """Manually-triggered (or Full Sync button) full-table pull for one
    source connection. See app.connectors.sync_engine - retries/backoff
    happen inside the connector itself, so this task does not retry the
    whole sync on failure."""
    from app.connectors import sync_engine
    from app.models.source_connection import SourceConnection

    db = SessionLocal()
    try:
        connection = db.query(SourceConnection).filter(SourceConnection.id == uuid.UUID(source_connection_id)).first()
        if connection is None:
            return {"error": "source connection not found"}
        batch = sync_engine.run_full_sync(db, connection)
        return {"batch_id": str(batch.id), "status": batch.status}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_source_incremental_sync", bind=True, max_retries=0)
def run_source_incremental_sync(self, source_connection_id: str) -> dict:
    """Sync Now / scheduled auto-sync path: only materials changed since
    the connection's last successful cursor."""
    from app.connectors import sync_engine
    from app.models.source_connection import SourceConnection

    db = SessionLocal()
    try:
        connection = db.query(SourceConnection).filter(SourceConnection.id == uuid.UUID(source_connection_id)).first()
        if connection is None:
            return {"error": "source connection not found"}
        batch = sync_engine.run_incremental_sync(db, connection)
        return {"batch_id": str(batch.id), "status": batch.status}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.check_due_source_syncs")
def check_due_source_syncs() -> dict:
    """
    Celery Beat entry point (see app.workers.celery_app's beat_schedule):
    on a short fixed tick, checks every enabled source connection's OWN
    sync_interval_seconds and enqueues an incremental sync for whichever
    ones are due - one periodic task driven entirely by per-row
    configuration rather than a hardcoded global interval (spec section 27).
    """
    from app.connectors import sync_engine

    db = SessionLocal()
    try:
        due = sync_engine.list_due_connections(db)
        for connection in due:
            run_source_incremental_sync.delay(str(connection.id))
        return {"triggered": len(due)}
    finally:
        db.close()
