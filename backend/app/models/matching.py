import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class MaterialMatch(Base, UUIDMixin, TimestampMixin):
    """A candidate pairing surfaced by vector search + detailed scoring."""

    __tablename__ = "material_matches"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )

    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    description_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    specification_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    category_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    uom_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    image_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    attribute_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    vector_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    material: Mapped["Material"] = relationship(foreign_keys=[material_id])
    candidate: Mapped["Material"] = relationship(foreign_keys=[candidate_material_id])


class AIAnalysis(Base, UUIDMixin, TimestampMixin):
    """Final AI decision produced for a material after evaluating all candidates."""

    __tablename__ = "ai_analysis"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    best_candidate_material_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=True
    )

    final_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    description_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    specification_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    category_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    uom_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    image_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    attribute_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    decision: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    reason_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_common_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    material: Mapped["Material"] = relationship(foreign_keys=[material_id])
    best_candidate: Mapped[Optional["Material"]] = relationship(foreign_keys=[best_candidate_material_id])
