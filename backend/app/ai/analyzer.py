"""
End-to-end AI harmonization pipeline orchestrator (spec sections 6-11, 28).

This is the only place that ties together: embedding generation, pgvector
candidate retrieval, detailed weighted scoring, technical-conflict
detection, XGBoost blending, the decision engine, and - critically - the
governance separation between an AI *recommendation* and a change to the
official Common Material Master (spec section 10/14). AI never writes
APPROVED directly; every mapping this module creates starts life as
AI_RECOMMENDED/PENDING_VALIDATION/MANUAL_REVIEW/TECHNICAL_CONFLICT and only
a human approval action (app.services.harmonization_service) can move it to
APPROVED/EDITED_AND_APPROVED. Every step is written to the audit log in the
same transaction.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.ai.conflict_detector import ConflictResult, detect_conflict, detect_structural_conflict
from app.ai.ml_ranker import blend_scores
from app.ai.similarity import find_candidate_materials
from app.ai.text_embeddings import generate_text_embedding
from app.models.enums import (
    ActorType,
    MappingDecisionStatus,
    MappingType,
    MatchDecision,
    MaterialStatus,
    NotificationType,
    RoleName,
)
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial, MaterialAttribute, MaterialEmbedding
from app.models.matching import AIAnalysis, MaterialMatch
from app.services.audit_service import log_action
from app.services.code_generator import generate_common_code
from app.services.decision_engine import evaluate
from app.services.notification_service import notify_role
from app.services.scoring import (
    ScoreBreakdown,
    classification_score as classification_score_fn,
    compute_final_score,
    cosine_similarity,
    criticality_score as criticality_score_fn,
    dimension_score as dimension_score_fn,
    field_is_applicable,
    field_text_score,
    function_score as function_score_fn,
    grade_score as grade_score_fn,
    manufacturer_is_applicable,
    manufacturer_score as manufacturer_score_fn,
    attribute_score as attr_score_fn,
    standard_score as standard_score_fn,
    uom_score as uom_score_fn,
)

logger = logging.getLogger(__name__)

# Decisions that establish some relationship worth recording as a mapping.
# NOT_EQUIVALENT records nothing - there is nothing to map.
_MAPPING_TYPE_BY_DECISION = {
    MatchDecision.IDENTICAL.value: MappingType.IDENTICAL.value,
    MatchDecision.DUPLICATE.value: MappingType.DUPLICATE.value,
    MatchDecision.NEAR_DUPLICATE.value: MappingType.NEAR_DUPLICATE.value,
    MatchDecision.FUNCTIONALLY_EQUIVALENT.value: MappingType.FUNCTIONALLY_EQUIVALENT.value,
    MatchDecision.MANUAL_REVIEW.value: MappingType.NEAR_DUPLICATE.value,
    MatchDecision.TECHNICAL_CONFLICT.value: MappingType.NEAR_DUPLICATE.value,
}

_DECISION_STATUS_BY_DECISION = {
    MatchDecision.IDENTICAL.value: MappingDecisionStatus.AI_RECOMMENDED.value,
    MatchDecision.DUPLICATE.value: MappingDecisionStatus.AI_RECOMMENDED.value,
    MatchDecision.NEAR_DUPLICATE.value: MappingDecisionStatus.PENDING_VALIDATION.value,
    MatchDecision.FUNCTIONALLY_EQUIVALENT.value: MappingDecisionStatus.PENDING_VALIDATION.value,
    MatchDecision.MANUAL_REVIEW.value: MappingDecisionStatus.MANUAL_REVIEW.value,
    MatchDecision.TECHNICAL_CONFLICT.value: MappingDecisionStatus.TECHNICAL_CONFLICT.value,
}

_ACTIVE_MAPPING_STATUSES = (
    MappingDecisionStatus.APPROVED.value,
    MappingDecisionStatus.EDITED_AND_APPROVED.value,
)


def _attributes_dict(db: Session, material_id: uuid.UUID) -> dict[str, str]:
    rows = db.query(MaterialAttribute).filter(MaterialAttribute.material_id == material_id).all()
    return {r.attr_key: r.attr_value for r in rows}


def ensure_embeddings(db: Session, material: CPSEMaterial) -> MaterialEmbedding:
    text_source = " ".join(
        filter(
            None,
            [
                material.normalized_description,
                material.normalized_specification,
                material.normalized_classification,
                material.material_grade or "",
                material.dimensions or "",
            ],
        )
    )
    text_vec, text_model = generate_text_embedding(text_source)

    embedding = material.embedding
    if embedding is None:
        embedding = MaterialEmbedding(material_id=material.id)
        db.add(embedding)
    embedding.text_embedding = text_vec
    embedding.embedding_model = text_model
    db.commit()
    db.refresh(embedding)
    return embedding


def _score_pair(
    db: Session,
    material: CPSEMaterial,
    embedding: MaterialEmbedding,
    attrs_a: dict[str, str],
    candidate: CPSEMaterial,
) -> tuple[ScoreBreakdown, float | None]:
    """Weighted score between `material` and one `candidate`. Returns (ScoreBreakdown, text_cosine)."""
    cand_embedding = candidate.embedding
    text_cos = cosine_similarity(
        embedding.text_embedding, cand_embedding.text_embedding if cand_embedding else None
    )

    description_score = field_text_score(
        material.normalized_description or "", candidate.normalized_description or "", text_cos
    )
    specification_score = field_text_score(
        material.normalized_specification or "", candidate.normalized_specification or "", text_cos
    )
    classification_score = classification_score_fn(
        material.normalized_classification or "", candidate.normalized_classification or ""
    )
    uom_score = uom_score_fn(material.normalized_uom or "", candidate.normalized_uom or "")
    attrs_b = _attributes_dict(db, candidate.id)
    attribute_score = attr_score_fn(attrs_a, attrs_b)
    grade_score = grade_score_fn(material.material_grade, candidate.material_grade)
    dimension_score = dimension_score_fn(material.dimensions, candidate.dimensions)
    standard_score = standard_score_fn(material.standard, candidate.standard)
    function_score = function_score_fn(material.function, candidate.function)
    criticality_score = criticality_score_fn(material.criticality, candidate.criticality)
    manufacturer_applicable = manufacturer_is_applicable(material.criticality, candidate.criticality)
    manufacturer_score = manufacturer_score_fn(material.manufacturer, candidate.manufacturer) if manufacturer_applicable else 0.0

    breakdown = compute_final_score(
        description_score=description_score,
        specification_score=specification_score,
        classification_score=classification_score,
        uom_score=uom_score,
        attribute_score=attribute_score,
        grade_score=grade_score,
        dimension_score=dimension_score,
        standard_score=standard_score,
        grade_applicable=field_is_applicable(material.material_grade, candidate.material_grade),
        dimension_applicable=field_is_applicable(material.dimensions, candidate.dimensions),
        standard_applicable=field_is_applicable(material.standard, candidate.standard),
        function_applicable=field_is_applicable(material.function, candidate.function),
        manufacturer_score=manufacturer_score,
        function_score=function_score,
        criticality_score=criticality_score,
        manufacturer_applicable=manufacturer_applicable,
    )
    return breakdown, text_cos


def _check_conflict(material: CPSEMaterial, candidate: CPSEMaterial) -> ConflictResult:
    text_a = f"{material.original_description} {material.technical_specification or ''}"
    text_b = f"{candidate.original_description} {candidate.technical_specification or ''}"
    text_result = detect_conflict(text_a, text_b)

    # Structured fields (spec section 9) - catches a grade/standard mismatch
    # even when a CPSE's source table never restates that value in the
    # free-text description/specification. Only meaningful when both
    # materials are already the same kind of thing (same normalized
    # classification) - e.g. a bolt's grade and a valve's grade have no
    # shared meaning to compare, so this would otherwise flag a false
    # conflict on every cross-category candidate pairing rather than a
    # genuine same-property mismatch.
    structural_result = ConflictResult(has_conflict=False, reasons=[])
    if (
        material.normalized_classification
        and material.normalized_classification == candidate.normalized_classification
    ):
        structural_result = detect_structural_conflict(
            {"material_grade": material.material_grade, "standard": material.standard},
            {"material_grade": candidate.material_grade, "standard": candidate.standard},
        )

    return ConflictResult(
        has_conflict=text_result.has_conflict or structural_result.has_conflict,
        reasons=text_result.reasons + structural_result.reasons,
    )


def _build_evidence(material: CPSEMaterial, candidate: CPSEMaterial, breakdown: ScoreBreakdown) -> dict:
    """Structured, non-fabricated evidence checklist (spec section 20) - a
    field is only ever reported as matching/specified when both materials
    actually carry a value for it; otherwise it is explicitly flagged as
    not specified rather than silently omitted or guessed."""

    def _field(name: str, value_a, value_b, score: float) -> dict:
        specified = bool(value_a) and bool(value_b)
        return {"specified": specified, "match": specified and score >= 90.0, "score": round(score, 2)}

    return {
        "material_type": _field("material_type", material.material_type, candidate.material_type, breakdown.classification_score),
        "grade": _field("grade", material.material_grade, candidate.material_grade, breakdown.grade_score),
        "dimension": _field("dimension", material.dimensions, candidate.dimensions, breakdown.dimension_score),
        "standard": _field("standard", material.standard, candidate.standard, breakdown.standard_score),
        "uom": _field("uom", material.uom, candidate.uom, breakdown.uom_score),
        "function": _field("function", material.function, candidate.function, breakdown.function_score),
        "manufacturer": _field("manufacturer", material.manufacturer, candidate.manufacturer, breakdown.manufacturer_score),
    }


def _find_reusable_common_material(material: CPSEMaterial, candidate: CPSEMaterial | None) -> CommonMaterial | None:
    """Idempotency (spec section 10/29): if either side of this pairing
    already has a non-rejected mapping, reuse that CommonMaterial instead of
    minting a new code - approved mappings win over merely-recommended ones."""
    candidates_mappings = list(material.mappings) + (list(candidate.mappings) if candidate else [])
    non_rejected = [m for m in candidates_mappings if m.decision_status != MappingDecisionStatus.REJECTED.value]
    if not non_rejected:
        return None
    approved = [m for m in non_rejected if m.decision_status in _ACTIVE_MAPPING_STATUSES]
    chosen = approved[0] if approved else non_rejected[0]
    return chosen.common_material


def _standardized_field(material: CPSEMaterial, candidate: CPSEMaterial | None, field: str):
    value = getattr(material, field, None)
    if value:
        return value
    return getattr(candidate, field, None) if candidate else None


def _handle_decision(
    db: Session,
    material: CPSEMaterial,
    analysis: AIAnalysis,
    best_candidate: CPSEMaterial | None,
    breakdown: ScoreBreakdown,
    decision_result,
) -> None:
    existing_active = next(
        (m for m in material.mappings if m.decision_status in _ACTIVE_MAPPING_STATUSES), None
    )
    if existing_active is not None:
        # A human has already approved this material's mapping. A rescan
        # (e.g. an incremental sync re-evaluating it) may still re-run, but
        # an approved mapping is authoritative and must never be silently
        # reassigned to a different code (spec section 10).
        log_action(
            db,
            action="RESCAN_SKIPPED_APPROVED_MAPPING",
            entity_type="cpse_material",
            entity_id=material.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            details={
                "material_code": material.original_material_code,
                "existing_common_code": existing_active.common_material.common_code,
                "decision": decision_result.decision,
            },
        )
        db.commit()
        return

    if decision_result.decision == MatchDecision.NOT_EQUIVALENT.value or best_candidate is None:
        db.commit()
        return

    common_material = _find_reusable_common_material(material, best_candidate)
    created_new_code = common_material is None
    if common_material is None:
        common_material = CommonMaterial(
            common_code=generate_common_code(db),
            material_type=_standardized_field(material, best_candidate, "material_type") or "GENERIC",
            classification=material.normalized_classification or best_candidate.normalized_classification or material.classification or "UNCLASSIFIED",
            standardized_description=material.original_description,
            standardized_specification=_standardized_field(material, best_candidate, "technical_specification"),
            material_grade=_standardized_field(material, best_candidate, "material_grade"),
            dimensions=_standardized_field(material, best_candidate, "dimensions"),
            standardized_uom=material.normalized_uom or material.uom,
            standard=_standardized_field(material, best_candidate, "standard"),
            function=_standardized_field(material, best_candidate, "function"),
            criticality=_standardized_field(material, best_candidate, "criticality") or "UNSPECIFIED",
            confidence=breakdown.final_score,
        )
        db.add(common_material)
        db.flush()

    mapping_type = _MAPPING_TYPE_BY_DECISION[decision_result.decision]
    decision_status = _DECISION_STATUS_BY_DECISION[decision_result.decision]
    evidence = _build_evidence(material, best_candidate, breakdown)

    mapping = (
        db.query(CommonMaterialMapping)
        .filter(CommonMaterialMapping.cpse_material_id == material.id)
        .filter(CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value)
        .order_by(CommonMaterialMapping.created_at.desc())
        .first()
    )
    if mapping is not None and mapping.common_material_id == common_material.id:
        mapping.mapping_type = mapping_type
        mapping.decision_status = decision_status
        mapping.confidence_score = breakdown.final_score
        mapping.evidence = evidence
        mapping.reason = decision_result.reason_text
        mapping.matched_against_material_id = best_candidate.id
        mapping.ai_analysis_id = analysis.id
        action = "MAPPING_REFRESHED"
    elif mapping is not None:
        mapping.common_material_id = common_material.id
        mapping.mapping_type = mapping_type
        mapping.decision_status = decision_status
        mapping.confidence_score = breakdown.final_score
        mapping.evidence = evidence
        mapping.reason = decision_result.reason_text
        mapping.matched_against_material_id = best_candidate.id
        mapping.ai_analysis_id = analysis.id
        action = "MAPPING_REASSIGNED"
    else:
        mapping = CommonMaterialMapping(
            common_material_id=common_material.id,
            cpse_material_id=material.id,
            matched_against_material_id=best_candidate.id,
            ai_analysis_id=analysis.id,
            mapping_type=mapping_type,
            decision_status=decision_status,
            confidence_score=breakdown.final_score,
            evidence=evidence,
            reason=decision_result.reason_text,
        )
        db.add(mapping)
        action = "MAPPING_CREATED"

    material.status = MaterialStatus.HARMONIZED.value
    analysis.recommended_common_code = common_material.common_code
    db.commit()
    db.refresh(mapping)

    log_action(
        db,
        action=action,
        entity_type="common_material_mapping",
        entity_id=mapping.id,
        actor_name="AI ENGINE",
        actor_type=ActorType.AI_ENGINE.value,
        after_state={"mapping_type": mapping_type, "decision_status": decision_status, "common_code": common_material.common_code},
        ai_model_version="rule-based+xgboost" if breakdown else None,
        confidence=breakdown.final_score,
        details={
            "material_code": material.original_material_code,
            "candidate_code": best_candidate.original_material_code,
            "common_code": common_material.common_code,
        },
    )

    if created_new_code:
        notify_role(
            db,
            RoleName.ADMIN.value,
            NotificationType.COMMON_CODE_GENERATED.value,
            "Common material code generated",
            f"{material.original_material_code} was linked to a new common code {common_material.common_code} "
            f"with {breakdown.final_score:.1f}% AI confidence ({decision_result.decision}).",
            "common_material",
            common_material.id,
        )
    if decision_status in (MappingDecisionStatus.PENDING_VALIDATION.value, MappingDecisionStatus.MANUAL_REVIEW.value):
        notify_role(
            db,
            RoleName.MATERIAL_EXPERT.value,
            NotificationType.HUMAN_APPROVAL_REQUIRED.value,
            "Human validation required",
            f"{material.original_material_code} matched {best_candidate.original_material_code} at "
            f"{breakdown.final_score:.1f}% confidence ({decision_result.decision}) - expert review required.",
            "common_material_mapping",
            mapping.id,
        )

    # Propagate settlement to the candidate side (reliability improvement,
    # not a new governance concept - spec section 28/29). The mapping just
    # created/updated above only links MATERIAL to this common material.
    # If `best_candidate` has no active mapping of its own, it must have
    # been analyzed earlier - before `material` existed or had an embedding
    # - and found nothing, so it would otherwise stay unmapped forever even
    # though it clearly belongs in the same group now. Re-analyzing it here
    # lets it discover `material` (which now has an embedding AND an active
    # mapping) as its own best candidate and reuse the same common material
    # via _find_reusable_common_material. This is exactly what makes a
    # burst of related materials synced moments apart - whether in the same
    # batch or across two independent CPSE syncs - converge automatically,
    # without a human needing to trigger the manual /harmonization/scan
    # rescan. It terminates naturally: it only ever continues through a
    # material that does NOT yet have a mapping, and a material never loses
    # one once it has it, so this can propagate at most once per
    # not-yet-mapped material in the whole database.
    candidate_has_active_mapping = any(
        m.decision_status != MappingDecisionStatus.REJECTED.value for m in best_candidate.mappings
    )
    if not candidate_has_active_mapping:
        try:
            from app.workers.tasks import ai_analysis

            ai_analysis.delay(str(best_candidate.id))
        except Exception:  # noqa: BLE001 - no broker reachable (isolated test/dev setup)
            analyze_material(db, best_candidate.id)


def analyze_material(db: Session, material_id: uuid.UUID) -> AIAnalysis:
    material = db.query(CPSEMaterial).filter(CPSEMaterial.id == material_id).first()
    if not material:
        raise ValueError(f"CPSEMaterial {material_id} not found")

    material.status = MaterialStatus.PROCESSING.value
    db.commit()

    try:
        embedding = ensure_embeddings(db, material)
        candidates = find_candidate_materials(db, material)
        attrs_a = _attributes_dict(db, material.id)

        db.query(MaterialMatch).filter(MaterialMatch.material_id == material.id).delete()

        scored: list[tuple[CPSEMaterial, ScoreBreakdown]] = []
        for candidate in candidates:
            breakdown, text_cos = _score_pair(db, material, embedding, attrs_a, candidate)

            db.add(
                MaterialMatch(
                    material_id=material.id,
                    candidate_material_id=candidate.id,
                    final_score=breakdown.final_score,
                    **{name: getattr(breakdown, name) for name in breakdown.as_dict() if name != "final_score"},
                    vector_distance=(1 - text_cos) if text_cos is not None else None,
                )
            )
            scored.append((candidate, breakdown))

        db.commit()

        if scored:
            best_candidate, best_breakdown = max(scored, key=lambda pair: pair[1].final_score)
        else:
            best_candidate, best_breakdown = None, compute_final_score(
                description_score=0, specification_score=0, classification_score=0, uom_score=0,
                attribute_score=0, grade_score=0, dimension_score=0, standard_score=0,
                manufacturer_score=0, function_score=0, criticality_score=0, manufacturer_applicable=False,
            )

        decision_breakdown, ml_result = blend_scores(best_breakdown)
        conflict = _check_conflict(material, best_candidate) if best_candidate else ConflictResult(False, [])
        decision_result = evaluate(
            decision_breakdown,
            material.original_description,
            best_candidate.original_description if best_candidate else "",
            conflict=conflict,
        )
        failure_reason = "No similar material found in the database for comparison." if not scored else None

        analysis = AIAnalysis(
            material_id=material.id,
            best_candidate_material_id=best_candidate.id if best_candidate else None,
            final_score=decision_breakdown.final_score,
            **{name: getattr(best_breakdown, name) for name in best_breakdown.as_dict() if name != "final_score"},
            decision=decision_result.decision,
            reason_text=decision_result.reason_text if scored else decision_result.message,
            status="COMPLETED",
            failure_reason=failure_reason,
            ml_probability=ml_result.score,
            ml_status=ml_result.status,
            technical_conflict=conflict.has_conflict,
            conflict_reason="; ".join(conflict.reasons) if conflict.reasons else None,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        if material.status != MaterialStatus.HARMONIZED.value:
            material.status = MaterialStatus.ANALYZED.value
            db.commit()

        log_action(
            db,
            action="AI_ANALYZED",
            entity_type="cpse_material",
            entity_id=material.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            ai_model_version="rule-based+xgboost",
            confidence=decision_breakdown.final_score,
            details={
                "final_score": decision_breakdown.final_score,
                "decision": decision_result.decision,
                "candidate": best_candidate.original_material_code if best_candidate else None,
                "ml_status": ml_result.status,
            },
        )

        _handle_decision(db, material, analysis, best_candidate, decision_breakdown, decision_result)

        return analysis

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        material = db.query(CPSEMaterial).filter(CPSEMaterial.id == material_id).first()
        material.status = MaterialStatus.FAILED.value
        analysis = AIAnalysis(
            material_id=material.id,
            final_score=0,
            description_score=0,
            specification_score=0,
            classification_score=0,
            uom_score=0,
            attribute_score=0,
            grade_score=0,
            dimension_score=0,
            standard_score=0,
            manufacturer_score=0,
            function_score=0,
            criticality_score=0,
            decision=MatchDecision.NOT_EQUIVALENT.value,
            reason_text="AI analysis could not determine a reliable match.",
            status="FAILED",
            failure_reason=str(exc),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        log_action(
            db,
            action="AI_ANALYSIS_FAILED",
            entity_type="cpse_material",
            entity_id=material.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            details={"error": str(exc)},
        )
        logger.exception("AI analysis failed for material %s", material_id)
        return analysis
