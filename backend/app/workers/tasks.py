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
