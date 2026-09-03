from pydantic import BaseModel


class DashboardStatistics(BaseModel):
    total_materials: int
    harmonized_materials: int
    pending_human_approvals: int
    cpses_onboarded: int
    duplicate_codes_reduced: int
    ai_recommendations: int
    common_codes_generated: int


class ChartPoint(BaseModel):
    label: str
    value: float


class ChartSeries(BaseModel):
    name: str
    points: list[ChartPoint]


class DashboardTrends(BaseModel):
    harmonization_progress: list[ChartPoint]
    confidence_distribution: list[ChartPoint]
    materials_by_cpse: list[ChartPoint]
    harmonized_by_cpse: list[ChartPoint]
    monthly_trend: list[ChartPoint]
    duplicate_reduction: list[ChartPoint]
    estimated_savings: list[ChartPoint]
