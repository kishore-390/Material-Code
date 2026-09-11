"""
Read-only "duplicate materials" reporting layer.

This does NOT introduce a new duplicate-detection mechanism. It re-derives
the exact same grouping the dashboard's "Duplicates Identified" KPI already
uses (common_material_mappings, populated entirely by the existing SBERT ->
pgvector -> XGBoost -> decision-engine pipeline in app.ai.analyzer) and
additionally reconstructs, for every "extra" material in a common-material
group, which specific pairing produced it - using the same ai_analysis /
material_matches rows the pipeline already wrote, never invented data.

count_duplicate_materials() is the single source of truth for the KPI
number; app.api.endpoints.dashboard imports it instead of keeping its own
copy, so the dashboard card and the harmonization pages can never drift
apart (spec section 37 - single source of truth).
"""
import dataclasses
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.matching import AIAnalysis, MaterialMatch

_NON_REJECTED = CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value


def _mappings_query(db: Session, mapping_types: tuple[str, ...] | None = None):
    query = db.query(CommonMaterialMapping).filter(_NON_REJECTED)
    if mapping_types:
        query = query.filter(CommonMaterialMapping.mapping_type.in_(mapping_types))
    return query


def count_duplicate_materials(db: Session) -> int:
    """For every common material with N active mappings, N-1 of them are
    "extra" (duplicate) records consolidated under that one code."""
    subq = (
        _mappings_query(db)
        .with_entities(CommonMaterialMapping.common_material_id, func.count(CommonMaterialMapping.id).label("cnt"))
        .group_by(CommonMaterialMapping.common_material_id)
        .subquery()
    )
    total_extra = db.query(func.coalesce(func.sum(subq.c.cnt - 1), 0)).scalar() or 0
    return int(total_extra)


@dataclasses.dataclass
class DuplicatePair:
    mapping_id: str
    common_material: CommonMaterial
    source: CPSEMaterial
    matched: CPSEMaterial
    mapping_type: str
    decision_status: str
    confidence_score: float | None
    breakdown: dict | None
    sbert_similarity: float | None
    ml_probability: float | None
    ml_status: str | None


def list_duplicate_pairs(
    db: Session, *, cpse_scope_id: uuid.UUID | None = None, mapping_types: tuple[str, ...] | None = None
) -> list[DuplicatePair]:
    """Every active mapping IS a duplicate/equivalence pair (material <->
    matched_against). Confidence/decision/component scores are always
    present here since a mapping is only ever created alongside an
    AIAnalysis or a human approval action - never fabricated."""
    query = (
        _mappings_query(db, mapping_types)
        .options(
            joinedload(CommonMaterialMapping.common_material),
            joinedload(CommonMaterialMapping.cpse_material).joinedload(CPSEMaterial.cpse),
            joinedload(CommonMaterialMapping.matched_against).joinedload(CPSEMaterial.cpse),
        )
        .filter(CommonMaterialMapping.matched_against_material_id.isnot(None))
    )
    if cpse_scope_id is not None:
        query = query.join(CPSEMaterial, CommonMaterialMapping.cpse_material_id == CPSEMaterial.id).filter(
            CPSEMaterial.cpse_id == cpse_scope_id
        )

    mappings = query.order_by(CommonMaterialMapping.created_at.desc()).all()
    if not mappings:
        return []

    member_ids = {m.cpse_material_id for m in mappings} | {m.matched_against_material_id for m in mappings}
    matches = (
        db.query(MaterialMatch)
        .filter(MaterialMatch.material_id.in_(member_ids), MaterialMatch.candidate_material_id.in_(member_ids))
        .order_by(MaterialMatch.created_at.desc())
        .all()
    )
    match_by_pair: dict[frozenset, MaterialMatch] = {}
    for match in matches:
        key = frozenset({match.material_id, match.candidate_material_id})
        match_by_pair.setdefault(key, match)

    results: list[DuplicatePair] = []
    seen_pairs: set[frozenset] = set()
    for mapping in mappings:
        key = frozenset({mapping.cpse_material_id, mapping.matched_against_material_id})
        # Spec section 5.3/5.4: each CPSE material that joins a group has
        # its own mapping row (A's row references B as matched_against, and
        # B's own row references A right back) - correct for "who belongs
        # to this common material", but a duplicate-PAIRS list should show
        # each unordered relationship once, not twice.
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        match = match_by_pair.get(key)
        sbert_similarity = round((1 - match.vector_distance) * 100, 2) if match and match.vector_distance is not None else None

        analysis = None
        if mapping.ai_analysis_id:
            analysis = db.query(AIAnalysis).filter(AIAnalysis.id == mapping.ai_analysis_id).first()

        breakdown = None
        if analysis is not None:
            breakdown = {
                "description_score": analysis.description_score,
                "specification_score": analysis.specification_score,
                "classification_score": analysis.classification_score,
                "uom_score": analysis.uom_score,
                "attribute_score": analysis.attribute_score,
                "grade_score": analysis.grade_score,
                "dimension_score": analysis.dimension_score,
                "standard_score": analysis.standard_score,
                "manufacturer_score": analysis.manufacturer_score,
                "function_score": analysis.function_score,
                "criticality_score": analysis.criticality_score,
            }

        results.append(
            DuplicatePair(
                mapping_id=str(mapping.id),
                common_material=mapping.common_material,
                source=mapping.cpse_material,
                matched=mapping.matched_against,
                mapping_type=mapping.mapping_type,
                decision_status=mapping.decision_status,
                confidence_score=mapping.confidence_score,
                breakdown=breakdown,
                sbert_similarity=sbert_similarity,
                ml_probability=analysis.ml_probability if analysis else None,
                ml_status=analysis.ml_status if analysis else None,
            )
        )
    return results


def get_duplicate_pair_by_mapping_id(
    db: Session, mapping_id: uuid.UUID, *, cpse_scope_id: uuid.UUID | None = None
) -> DuplicatePair | None:
    for pair in list_duplicate_pairs(db, cpse_scope_id=cpse_scope_id):
        if pair.mapping_id == str(mapping_id):
            return pair
    return None
