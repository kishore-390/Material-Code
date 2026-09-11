from app.core.config import settings
from app.db.session import SessionLocal
from app.models.settings import SystemSetting

DEFAULTS = {
    "threshold_auto": settings.THRESHOLD_AUTO,
    "threshold_review": settings.THRESHOLD_REVIEW,
    "threshold_low": settings.THRESHOLD_LOW,
    "weight_description": settings.WEIGHT_DESCRIPTION,
    "weight_specification": settings.WEIGHT_SPECIFICATION,
    "weight_classification": settings.WEIGHT_CLASSIFICATION,
    "weight_uom": settings.WEIGHT_UOM,
    "weight_attributes": settings.WEIGHT_ATTRIBUTES,
    "weight_grade": settings.WEIGHT_GRADE,
    "weight_dimension": settings.WEIGHT_DIMENSION,
    "weight_standard": settings.WEIGHT_STANDARD,
    "weight_manufacturer": settings.WEIGHT_MANUFACTURER,
    "weight_function": settings.WEIGHT_FUNCTION,
    "weight_criticality": settings.WEIGHT_CRITICALITY,
}


def get_all_settings() -> dict:
    db = SessionLocal()
    try:
        rows = db.query(SystemSetting).all()
        values = dict(DEFAULTS)
        for row in rows:
            if row.key in values:
                try:
                    values[row.key] = float(row.value)
                except ValueError:
                    pass
        return values
    finally:
        db.close()


def get_effective_thresholds() -> dict:
    values = get_all_settings()
    return {
        "auto": values["threshold_auto"],
        "review": values["threshold_review"],
        "low": values["threshold_low"],
    }


def get_effective_weights() -> dict:
    values = get_all_settings()
    return {
        "description": values["weight_description"],
        "specification": values["weight_specification"],
        "classification": values["weight_classification"],
        "uom": values["weight_uom"],
        "attributes": values["weight_attributes"],
        "grade": values["weight_grade"],
        "dimension": values["weight_dimension"],
        "standard": values["weight_standard"],
        "manufacturer": values["weight_manufacturer"],
        "function": values["weight_function"],
        "criticality": values["weight_criticality"],
    }


def update_settings(updates: dict, db) -> dict:
    for key, value in updates.items():
        if value is None or key not in DEFAULTS:
            continue
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(SystemSetting(key=key, value=str(value), description=f"Override for {key}"))
    db.commit()
    return get_all_settings()
