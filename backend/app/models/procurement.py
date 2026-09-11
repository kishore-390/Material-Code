import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDMixin


class ProcurementHistory(Base, UUIDMixin, TimestampMixin):
    """
    Historical procurement data for one CPSE material (spec section 5.5) -
    the raw input that procurement-aggregation analytics (spec section 15)
    reads. is_demo_data marks rows created by app.demo_seed so they can
    never be mistaken for real CPSE procurement records (spec section 33).
    """

    __tablename__ = "procurement_history"

    cpse_material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cpse_materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    procurement_reference: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    uom: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    vendor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plant_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    is_demo_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    cpse_material: Mapped["CPSEMaterial"] = relationship(back_populates="procurement_records")
