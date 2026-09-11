from pydantic import BaseModel


class SystemSettingsOut(BaseModel):
    threshold_auto: float
    threshold_review: float
    threshold_low: float
    weight_description: float
    weight_specification: float
    weight_classification: float
    weight_uom: float
    weight_attributes: float
    weight_grade: float
    weight_dimension: float
    weight_standard: float
    weight_manufacturer: float
    weight_function: float
    weight_criticality: float


class SystemSettingsUpdate(BaseModel):
    threshold_auto: float | None = None
    threshold_review: float | None = None
    threshold_low: float | None = None
    weight_description: float | None = None
    weight_specification: float | None = None
    weight_classification: float | None = None
    weight_uom: float | None = None
    weight_attributes: float | None = None
    weight_grade: float | None = None
    weight_dimension: float | None = None
    weight_standard: float | None = None
    weight_manufacturer: float | None = None
    weight_function: float | None = None
    weight_criticality: float | None = None
