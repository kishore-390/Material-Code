import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Governance audit trail (spec section 5.8 / 25). Every important
    change - mapping approvals, common-code changes, sync outcomes - is
    recorded here with enough structure to reconstruct before/after state
    without relying on free-form `details` alone."""

    __tablename__ = "audit_logs"

    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_name: Mapped[str] = mapped_column(String(255), nullable=False, default="AI ENGINE")
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    before_state: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    ai_model_version: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    actor: Mapped[Optional["User"]] = relationship()
