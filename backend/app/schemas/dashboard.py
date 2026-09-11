from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DashboardStatistics(BaseModel):
    """spec section 18 KPIs."""

    cpses_connected: int
    total_materials: int
    common_material_codes: int
    duplicates_identified: int
    near_duplicates: int
    functionally_equivalent: int
    pending_validation: int
    legacy_codes_rationalized: int
    potential_procurement_aggregation_value: float
    technical_conflicts: int
    new_materials_today: int
    last_synchronization: Optional[datetime] = None


class ChartPoint(BaseModel):
    label: str
    value: float


class DashboardTrends(BaseModel):
    materials_by_cpse: list[ChartPoint]
    duplicate_reduction: list[ChartPoint]
    common_code_adoption: list[ChartPoint]
    harmonization_progress: list[ChartPoint]
    cpse_contribution: list[ChartPoint]
    procurement_aggregation_opportunities: list[ChartPoint]
