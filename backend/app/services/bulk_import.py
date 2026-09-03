import io
import math
import uuid

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.cpse import CPSEOrganization
from app.models.material import Material
from app.models.enums import MaterialStatus
from app.services import normalization

REQUIRED_COLUMNS = [
    "material_code", "description", "specification", "category",
    "uom", "cpse", "manufacturer", "brand", "material_type", "image",
]


def read_upload_dataframe(file: UploadFile) -> pd.DataFrame:
    filename = (file.filename or "").lower()
    content = file.file.read()
    file.file.seek(0)
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    elif filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df


def _clean(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def validate_dataframe(db: Session, df: pd.DataFrame) -> list[dict]:
    known_cpse_codes = {row.code for row in db.query(CPSEOrganization.code).all()}
    seen_in_file: set[tuple[str, str]] = set()
    results: list[dict] = []

    for idx, row in df.iterrows():
        errors: list[str] = []
        data = {col: _clean(row.get(col)) for col in REQUIRED_COLUMNS}

        code = data["material_code"]
        description = data["description"]
        uom = data["uom"]
        category = data["category"]
        cpse_code = (data["cpse"] or "").upper()

        if not code:
            errors.append("Missing material code")
        if not description:
            errors.append("Missing description")
        if not category:
            errors.append("Missing category")
        if not uom:
            errors.append("Missing UOM")
        if not cpse_code:
            errors.append("Missing CPSE")
        elif cpse_code not in known_cpse_codes:
            errors.append(f"Unknown CPSE '{cpse_code}'")

        if code and cpse_code:
            key = (code, cpse_code)
            if key in seen_in_file:
                errors.append("Duplicate material code within uploaded file")
            seen_in_file.add(key)

            exists = (
                db.query(Material)
                .join(CPSEOrganization)
                .filter(Material.material_code == code, CPSEOrganization.code == cpse_code)
                .first()
            )
            if exists:
                errors.append("Duplicate material code already exists for this CPSE")

        results.append(
            {
                "row_number": int(idx) + 1,
                "data": data,
                "errors": errors,
                "is_valid": len(errors) == 0,
            }
        )
    return results


def import_valid_rows(db: Session, valid_rows: list[dict], created_by: uuid.UUID | None) -> list[uuid.UUID]:
    cpse_by_code = {c.code: c for c in db.query(CPSEOrganization).all()}
    created_ids: list[uuid.UUID] = []

    for row in valid_rows:
        data = row["data"]
        cpse = cpse_by_code.get((data["cpse"] or "").upper())
        if not cpse:
            continue
        material = Material(
            material_code=data["material_code"],
            description=data["description"],
            normalized_description=normalization.normalize_description(data["description"]),
            specification=data.get("specification"),
            normalized_specification=normalization.normalize_specification(data.get("specification")),
            category=data["category"],
            normalized_category=normalization.normalize_category(data["category"]),
            uom=data["uom"],
            normalized_uom=normalization.normalize_uom(data["uom"]),
            cpse_id=cpse.id,
            manufacturer=data.get("manufacturer"),
            brand=data.get("brand"),
            material_type=data.get("material_type"),
            status=MaterialStatus.PENDING.value,
            image_url=data.get("image"),
            created_by=created_by,
        )
        db.add(material)
        db.flush()
        created_ids.append(material.id)

    db.commit()
    return created_ids
