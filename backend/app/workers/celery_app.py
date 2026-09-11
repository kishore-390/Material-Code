from celery import Celery

from app.core.config import settings

# Import the full model registry so every SQLAlchemy relationship() string
# forward-reference (e.g. CPSEMaterial.cpse -> "CPSE") can resolve inside
# the worker process, which otherwise only imports the handful of model
# modules that app.ai.analyzer touches directly.
from app.db.base import Base  # noqa: F401,E402

celery_app = Celery(
    "material_harmonization",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=100,
)

# Celery Beat: a single fixed-interval tick that checks every source
# connection's OWN configurable sync_interval_seconds
# (app.connectors.sync_engine.list_due_connections) and enqueues incremental
# syncs for whichever are due - not a per-connection Beat schedule entry, so
# adding/editing a connection's interval never requires restarting Beat.
celery_app.conf.beat_schedule = {
    "check-due-source-syncs": {
        "task": "app.workers.tasks.check_due_source_syncs",
        "schedule": settings.SOURCE_SYNC_BEAT_TICK_SECONDS,
    },
}
