import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class CommonMaterialCode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "common_material_codes"

    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    material_type: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    standard_description: Mapped[str] = mapped_column(Text, nullable=False)
    standard_specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uom: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="AUTO_GENERATED", index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    materials: Mapped[list["Material"]] = relationship(back_populates="common_code")


class HarmonizationRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "harmonization_requests"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_material_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True
    )
    ai_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_analysis.id"), nullable=True
    )
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    request_type: Mapped[str] = mapped_column(String(20), nullable=False, default="AI_AUTO")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    common_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("common_material_codes.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    material: Mapped["Material"] = relationship(foreign_keys=[material_id])
    candidate: Mapped[Optional["Material"]] = relationship(foreign_keys=[candidate_material_id])
    common_code: Mapped[Optional["CommonMaterialCode"]] = relationship(foreign_keys=[common_code_id])
