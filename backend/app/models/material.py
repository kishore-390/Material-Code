import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base_class import Base, TimestampMixin, UUIDMixin
from app.models.enums import MaterialStatus


class Material(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materials"

    material_code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_specification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    normalized_category: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    uom: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    normalized_uom: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    cpse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpse_organizations.id"), nullable=False, index=True
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    material_type: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=MaterialStatus.PENDING.value, index=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    common_code_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("common_material_codes.id"), nullable=True, index=True
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Source-system provenance (spec: "fetch by code" from an external CPSE ERP/database
    # rather than manual entry). Null for materials created by hand or CSV/Excel upload.
    source_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_database: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_material_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    cpse: Mapped["CPSEOrganization"] = relationship(back_populates="materials")
    common_code: Mapped[Optional["CommonMaterialCode"]] = relationship(back_populates="materials")
    attributes: Mapped[list["MaterialAttribute"]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )
    images: Mapped[list["MaterialImage"]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )
    embedding: Mapped[Optional["MaterialEmbedding"]] = relationship(
        back_populates="material", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_materials_code_cpse", "material_code", "cpse_id", unique=True),
    )


class MaterialAttribute(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "material_attributes"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attr_key: Mapped[str] = mapped_column(String(150), nullable=False)
    attr_value: Mapped[str] = mapped_column(String(500), nullable=False)

    material: Mapped["Material"] = relationship(back_populates="attributes")


class MaterialImage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "material_images"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(default=False)

    material: Mapped["Material"] = relationship(back_populates="images")


class MaterialEmbedding(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "material_embeddings"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("materials.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    text_embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.EMBEDDING_DIM), nullable=True
    )
    image_embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(settings.IMAGE_EMBEDDING_DIM), nullable=True
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    material: Mapped["Material"] = relationship(back_populates="embedding")
