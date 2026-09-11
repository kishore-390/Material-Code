import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base_class import Base, TimestampMixin, UUIDMixin
from app.models.enums import MaterialStatus


class CPSEMaterial(Base, UUIDMixin, TimestampMixin):
    """
    A material record as it exists in one CPSE's own material master (spec
    section 5.2). This is the CPSE's original data, always preserved
    unmodified in original_material_code/original_description - the AI's
    standardized interpretation lives separately on CommonMaterial.
    Never assume this code is unique outside its own CPSE.
    """

    __tablename__ = "cpse_materials"

    cpse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpses.id"), nullable=False, index=True
    )
    original_material_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

    material_type: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    material_grade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dimensions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    technical_specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    uom: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    normalized_uom: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    standard: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    function: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    classification: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    normalized_classification: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    # Structured hierarchy, e.g. ["Mechanical", "Fasteners", "Bolts"] (spec section 12).
    classification_path: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    packaging: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    criticality: Mapped[str] = mapped_column(String(30), nullable=False, default="UNSPECIFIED")
    quantity: Mapped[Optional[float]] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=MaterialStatus.PENDING.value, index=True
    )
    # Marks a row created by the demo-only CSV import mechanism
    # (app.services.csv_import_service) - never set for materials that
    # arrived through a real source_connections sync. Mirrors the existing
    # ProcurementHistory.is_demo_data field/naming (spec section 33).
    is_demo_data: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    # Source-system timestamps (the CPSE's own record of when the row was
    # created/changed), distinct from last_synced_at (when WE last pulled it).
    source_created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    source_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_connections.id"), nullable=True, index=True
    )
    sync_history_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sync_history.id"), nullable=True, index=True
    )

    cpse: Mapped["CPSE"] = relationship(back_populates="materials")
    attributes: Mapped[list["MaterialAttribute"]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )
    embedding: Mapped[Optional["MaterialEmbedding"]] = relationship(
        back_populates="material", uselist=False, cascade="all, delete-orphan"
    )
    mappings: Mapped[list["CommonMaterialMapping"]] = relationship(
        back_populates="cpse_material", foreign_keys="CommonMaterialMapping.cpse_material_id"
    )
    procurement_records: Mapped[list["ProcurementHistory"]] = relationship(back_populates="cpse_material")

    __table_args__ = (
        Index("ix_cpse_materials_code_cpse", "original_material_code", "cpse_id", unique=True),
    )


class MaterialAttribute(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "material_attributes"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attr_key: Mapped[str] = mapped_column(String(150), nullable=False)
    attr_value: Mapped[str] = mapped_column(String(500), nullable=False)

    material: Mapped["CPSEMaterial"] = relationship(back_populates="attributes")


class MaterialEmbedding(Base, UUIDMixin, TimestampMixin):
    """Text-only embedding store. Image embeddings were removed along with
    the manual-upload workflow that was their only source of photos - CPSE
    ERP/SAP material masters are text/numeric records, not images."""

    __tablename__ = "material_embeddings"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cpse_materials.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    text_embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIM), nullable=True
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    material: Mapped["CPSEMaterial"] = relationship(back_populates="embedding")
