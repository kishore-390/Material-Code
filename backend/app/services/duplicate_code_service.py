"""
Duplicate SOURCE MATERIAL CODE detection - a deliberately separate concept
from app.services.duplicate_service (AI-detected material EQUIVALENCE,
tracked via common_material_mappings). Here, "duplicate" means the exact
same literal original_material_code string was supplied by two or more
different CPSEs - which does NOT by itself imply the underlying materials
are the same physical item (spec section 13 - legacy code rationalization
needs this distinction). See classify_pair() for how the two concepts are
reconciled for display.

Read-only: one grouped SQL query over the existing cpse_materials table, no
new table, no new counting mechanism.
"""
import dataclasses

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.ai.conflict_detector import detect_conflict, detect_structural_conflict
from app.models.enums import MappingDecisionStatus
from app.models.material import CPSEMaterial

SAME_SOURCE_CODE = "SAME_SOURCE_CODE"
AI_TECHNICAL_EQUIVALENCE = "AI_TECHNICAL_EQUIVALENCE"
TECHNICAL_CONFLICT = "TECHNICAL_CONFLICT"


@dataclasses.dataclass
class DuplicateCodeGroup:
    original_material_code: str
    materials: list[CPSEMaterial]


def _grouped_codes_query(db: Session):
    return (
        db.query(CPSEMaterial.original_material_code)
        .group_by(CPSEMaterial.original_material_code)
        .having(func.count(func.distinct(CPSEMaterial.cpse_id)) > 1)
    )


def count_duplicate_codes_summary(db: Session) -> dict:
    codes = [row[0] for row in _grouped_codes_query(db).all()]
    if not codes:
        return {"total_duplicate_codes": 0, "cpses_affected": 0, "materials_affected": 0}

    materials = db.query(CPSEMaterial).filter(CPSEMaterial.original_material_code.in_(codes)).all()
    return {
        "total_duplicate_codes": len(codes),
        "cpses_affected": len({m.cpse_id for m in materials}),
        "materials_affected": len(materials),
    }


def list_duplicate_code_groups(db: Session, *, q: str | None = None) -> list[DuplicateCodeGroup]:
    codes_query = _grouped_codes_query(db)
    if q:
        codes_query = codes_query.filter(CPSEMaterial.original_material_code.ilike(f"%{q.strip()}%"))
    codes = [row[0] for row in codes_query.order_by(CPSEMaterial.original_material_code).all()]
    if not codes:
        return []

    materials = (
        db.query(CPSEMaterial)
        .options(joinedload(CPSEMaterial.cpse), joinedload(CPSEMaterial.attributes), joinedload(CPSEMaterial.mappings))
        .filter(CPSEMaterial.original_material_code.in_(codes))
        .order_by(CPSEMaterial.original_material_code, CPSEMaterial.cpse_id)
        .all()
    )

    grouped: dict[str, list[CPSEMaterial]] = {}
    for m in materials:
        grouped.setdefault(m.original_material_code, []).append(m)

    return [DuplicateCodeGroup(original_material_code=code, materials=grouped[code]) for code in codes if code in grouped]


def get_duplicate_code_group(db: Session, original_material_code: str) -> DuplicateCodeGroup | None:
    materials = (
        db.query(CPSEMaterial)
        .options(joinedload(CPSEMaterial.cpse), joinedload(CPSEMaterial.attributes), joinedload(CPSEMaterial.mappings))
        .filter(CPSEMaterial.original_material_code == original_material_code)
        .order_by(CPSEMaterial.cpse_id)
        .all()
    )
    if len({m.cpse_id for m in materials}) < 2:
        return None
    return DuplicateCodeGroup(original_material_code=original_material_code, materials=materials)


def _active_common_material_id(material: CPSEMaterial):
    active = [m for m in material.mappings if m.decision_status != MappingDecisionStatus.REJECTED.value]
    return active[0].common_material_id if active else None


def classify_pair(a: CPSEMaterial, b: CPSEMaterial) -> str:
    common_a, common_b = _active_common_material_id(a), _active_common_material_id(b)
    if common_a is not None and common_a == common_b:
        return AI_TECHNICAL_EQUIVALENCE

    text_a = f"{a.original_description} {a.technical_specification or ''}"
    text_b = f"{b.original_description} {b.technical_specification or ''}"
    structural_conflict = False
    if a.normalized_classification and a.normalized_classification == b.normalized_classification:
        structural_conflict = detect_structural_conflict(
            {"material_grade": a.material_grade, "standard": a.standard},
            {"material_grade": b.material_grade, "standard": b.standard},
        ).has_conflict
    if detect_conflict(text_a, text_b).has_conflict or structural_conflict:
        return TECHNICAL_CONFLICT

    return SAME_SOURCE_CODE
