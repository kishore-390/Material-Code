import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class ApprovalRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    harmonization_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("harmonization_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    candidate_material_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True
    )
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    material: Mapped["Material"] = relationship(foreign_keys=[material_id])
    candidate: Mapped[Optional["Material"]] = relationship(foreign_keys=[candidate_material_id])
    actions: Mapped[list["ApprovalAction"]] = relationship(
        back_populates="approval_request", cascade="all, delete-orphan"
    )


class ApprovalAction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_actions"

    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    approval_request: Mapped["ApprovalRequest"] = relationship(back_populates="actions")
    actor: Mapped["User"] = relationship()

    @property
    def actor_name(self) -> str:
        return self.actor.full_name if self.actor else "Unknown"
