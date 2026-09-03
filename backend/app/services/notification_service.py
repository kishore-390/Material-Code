import uuid

from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify_user(
    db: Session,
    user_id: uuid.UUID | None,
    type_: str,
    title: str,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
    role_target: str | None = None,
) -> Notification:
    note = Notification(
        user_id=user_id,
        role_target=role_target,
        type=type_,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def notify_role(
    db: Session,
    role_name: str,
    type_: str,
    title: str,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: uuid.UUID | None = None,
) -> Notification:
    return notify_user(
        db,
        user_id=None,
        type_=type_,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        role_target=role_name,
    )
