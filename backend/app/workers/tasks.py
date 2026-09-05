"""
Celery background jobs (spec section 22).

Every material - whether uploaded one at a time or as part of a
10,000-row bulk import - gets its AI analysis queued here instead of
blocking the HTTP request. `ai_analysis` is the single entry point; it
internally performs embedding generation, pgvector similarity search,
detailed scoring and the decision-engine step (see app.ai.analyzer).
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


@celery_app.task(name="app.workers.tasks.process_bulk_import", bind=True, max_retries=1)
def process_bulk_import(self, upload_batch_id: str, rows: list[dict], created_by: str | None) -> dict:
    """
    Runs the row-insertion step of a bulk material upload in the background
    (spec section 22 / dynamic upload redesign) so the HTTP request that
    triggers a multi-thousand-row import never blocks on it. Reuses
    bulk_import.import_valid_rows unchanged, then queues AI analysis for
    every created material exactly as the synchronous path always has.
    """
    import uuid as uuid_module
    from datetime import datetime, timezone

    from app.models.enums import UploadStatus
    from app.models.upload_batch import UploadBatch
    from app.services import bulk_import

    db = SessionLocal()
    try:
        batch = db.query(UploadBatch).filter(UploadBatch.id == uuid_module.UUID(upload_batch_id)).first()
        if batch is None:
            return {"error": "upload batch not found"}

        batch.status = UploadStatus.PROCESSING.value
        db.commit()

        try:
            created_ids = bulk_import.import_valid_rows(
                db, rows, uuid_module.UUID(created_by) if created_by else None
            )
        except Exception as exc:  # noqa: BLE001
            batch.status = UploadStatus.FAILED.value
            batch.error_message = str(exc)
            batch.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise

        batch.valid_records = len(created_ids)
        batch.status = (
            UploadStatus.COMPLETED.value if len(created_ids) == batch.total_records else UploadStatus.PARTIAL.value
        )
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()

        for material_id in created_ids:
            ai_analysis.delay(str(material_id))

        return {"upload_batch_id": upload_batch_id, "imported": len(created_ids), "status": batch.status}
    finally:
        db.close()
