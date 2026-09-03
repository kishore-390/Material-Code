from pydantic import BaseModel


class SystemSettingsOut(BaseModel):
    threshold_auto: float
    threshold_review: float
    threshold_low: float
    weight_description: float
    weight_specification: float
    weight_category: float
    weight_uom: float
    weight_image: float
    weight_attributes: float


class SystemSettingsUpdate(BaseModel):
    threshold_auto: float | None = None
    threshold_review: float | None = None
    threshold_low: float | None = None
    weight_description: float | None = None
    weight_specification: float | None = None
    weight_category: float | None = None
    weight_uom: float | None = None
    weight_image: float | None = None
    weight_attributes: float | None = None
