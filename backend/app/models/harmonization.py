import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin
from app.models.enums import CommonMaterialStatus


class CommonMaterial(Base, UUIDMixin, TimestampMixin):
    """
    The neutral, standardized National Common Material record (spec section
    5.3). Never a renamed CPSE code - common_code always comes from
    app.services.code_generator's DB-sequence-backed generator. Fields here
    are the AI-recommended/human-approved STANDARDIZED representation;
    original per-CPSE values always remain on CPSEMaterial, never
    overwritten by this record.
    """

    __tablename__ = "common_materials"

    common_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    standardized_description: Mapped[str] = mapped_column(Text, nullable=False)
    standardized_specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    material_type: Mapped[str] = mapped_column(String(150), nullable=False)
    material_grade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dimensions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    standardized_uom: Mapped[str] = mapped_column(String(50), nullable=False)
    standard: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    function: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    criticality: Mapped[str] = mapped_column(String(30), nullable=False, default="UNSPECIFIED")

    classification: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    classification_path: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Lifecycle status (spec section 13) - distinct from any single mapping's
    # decision_status, which lives on CommonMaterialMapping.
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=CommonMaterialStatus.ACTIVE.value, index=True
    )
    # Aggregate/informational confidence across all mappings into this code -
    # never authoritative on its own; the per-mapping confidence_score is.
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    mappings: Mapped[list["CommonMaterialMapping"]] = relationship(back_populates="common_material")


class CommonMaterialMapping(Base, UUIDMixin, TimestampMixin):
    """
    The single authoritative link between one CPSEMaterial and one
    CommonMaterial (spec section 5.4) - this table IS the harmonization
    result and the object every approval action acts on. Consolidates what
    used to be two overlapping state machines (HarmonizationRequest +
    ApprovalRequest) into one, per the single-source-of-truth principle
    (spec section 37).
    """

    __tablename__ = "common_material_mappings"

    common_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("common_materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cpse_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The other CPSE material this mapping was derived from comparing
    # against (the AI's "best candidate"), when applicable.
    matched_against_material_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpse_materials.id"), nullable=True
    )
    ai_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_analysis.id"), nullable=True
    )

    mapping_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    decision_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Structured evidence (attribute-by-attribute match/mismatch), never fabricated -
    # missing attributes are represented explicitly (spec section 11/20).
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    common_material: Mapped["CommonMaterial"] = relationship(back_populates="mappings")
    cpse_material: Mapped["CPSEMaterial"] = relationship(
        back_populates="mappings", foreign_keys=[cpse_material_id]
    )
    matched_against: Mapped[Optional["CPSEMaterial"]] = relationship(
        foreign_keys=[matched_against_material_id]
    )
    actions: Mapped[list["ApprovalAction"]] = relationship(
        back_populates="mapping", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # One row per (common_material, cpse_material) pair - re-evaluating the
        # same pair updates the existing mapping rather than creating a new one.
        UniqueConstraint("common_material_id", "cpse_material_id", name="uq_mapping_common_cpse_material"),
    )
