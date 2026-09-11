import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import ActorType


def log_action(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    actor_id: uuid.UUID | None = None,
    actor_name: str = "AI ENGINE",
    actor_type: str = ActorType.AI_ENGINE.value,
    before_state: dict | None = None,
    after_state: dict | None = None,
    reason: str | None = None,
    ai_model_version: str | None = None,
    confidence: float | None = None,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=actor_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        reason=reason,
        ai_model_version=ai_model_version,
        confidence=confidence,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
