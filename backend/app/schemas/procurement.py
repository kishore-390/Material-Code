import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ProcurementRecordOut(BaseModel):
    id: uuid.UUID
    cpse_material_id: uuid.UUID
    procurement_reference: Optional[str] = None
    purchase_date: Optional[date] = None
    quantity: float
    uom: Optional[str] = None
    unit_price: Optional[float] = None
    currency: str
    vendor: Optional[str] = None
    plant_location: Optional[str] = None
    is_demo_data: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CPSEDemand(BaseModel):
    cpse_code: str
    cpse_name: str
    total_quantity: float
    uom: Optional[str] = None


class CollaborativeProcurementOpportunity(BaseModel):
    """spec section 15 - never a claim of actual savings, only a
    potential-aggregation estimate derived from real (or clearly
    demo-flagged) procurement_history rows."""

    common_code: str
    standardized_description: str
    cpse_demand: list[CPSEDemand]
    total_potential_aggregated_demand: float
    uom: Optional[str] = None
    includes_demo_data: bool
    note: str = "Estimated opportunity - potential procurement aggregation, not a realized saving."
