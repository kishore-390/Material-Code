import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class ApprovalAction(Base, UUIDMixin, TimestampMixin):
    """The audit trail of human decisions taken against one
    CommonMaterialMapping (approve/reject/edit-and-approve/manual-review/
    request-more-info) - spec section 14."""

    __tablename__ = "approval_actions"

    mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("common_material_mappings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    mapping: Mapped["CommonMaterialMapping"] = relationship(back_populates="actions")
    actor: Mapped["User"] = relationship()

    @property
    def actor_name(self) -> str:
        return self.actor.full_name if self.actor else "Unknown"
