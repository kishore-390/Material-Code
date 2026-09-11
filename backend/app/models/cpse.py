from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin
from app.models.enums import SynchronizationStatus


class CPSE(Base, UUIDMixin, TimestampMixin):
    """A Central Public Sector Enterprise participating in the national
    material master. The CPSE always remains the owner of its own original
    material master - this row never holds material data itself, only
    identity/sector/sync-health (spec section 5.1)."""

    __tablename__ = "cpses"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    synchronization_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SynchronizationStatus.NEVER_SYNCED.value
    )

    users: Mapped[list["User"]] = relationship(back_populates="cpse")
    materials: Mapped[list["CPSEMaterial"]] = relationship(back_populates="cpse")
    source_connections: Mapped[list["SourceConnection"]] = relationship(back_populates="cpse")
