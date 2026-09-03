"""
End-to-end AI analysis pipeline orchestrator (spec sections 7-10).

This is the only place that ties together: embedding generation,
pgvector candidate retrieval, detailed weighted scoring, the decision
engine, and -- critically -- the governance separation between an AI
*recommendation* and a change to the official Common Material Master.
Only the AUTO_HARMONIZATION path writes to the master directly, and even
then every step is written to the audit log in the same transaction.
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.ai.image_embeddings import generate_image_embedding
from app.ai.similarity import find_candidate_materials
from app.ai.text_embeddings import generate_text_embedding
from app.models.approval import ApprovalRequest
from app.models.enums import (
    ActorType,
    ApprovalStatus,
    Decision,
    HarmonizationStatus,
    MaterialStatus,
    NotificationType,
    RoleName,
)
from app.models.harmonization import CommonMaterialCode, HarmonizationRequest
from app.models.material import Material, MaterialAttribute, MaterialEmbedding
from app.models.matching import AIAnalysis, MaterialMatch
from app.services.audit_service import log_action
from app.services.code_generator import generate_common_code
from app.services.decision_engine import evaluate
from app.services.notification_service import notify_role, notify_user
from app.services.scoring import (
    attribute_score as attr_score_fn,
    category_score as cat_score_fn,
    compute_final_score,
    cosine_similarity,
    field_text_score,
    image_score as img_score_fn,
    uom_score as uom_score_fn,
)

logger = logging.getLogger(__name__)


def _attributes_dict(db: Session, material_id: uuid.UUID) -> dict[str, str]:
    rows = db.query(MaterialAttribute).filter(MaterialAttribute.material_id == material_id).all()
    return {r.attr_key: r.attr_value for r in rows}


def ensure_embeddings(db: Session, material: Material) -> MaterialEmbedding:
    text_source = " ".join(
        filter(
            None,
            [
                material.normalized_description,
                material.normalized_specification,
                material.normalized_category,
                material.manufacturer or "",
                material.brand or "",
            ],
        )
    )
    text_vec, text_model = generate_text_embedding(text_source)
    image_vec, image_model = generate_image_embedding(material.image_url)

    embedding = material.embedding
    if embedding is None:
        embedding = MaterialEmbedding(material_id=material.id)
        db.add(embedding)
    embedding.text_embedding = text_vec
    embedding.image_embedding = image_vec
    embedding.embedding_model = text_model + (f"+{image_model}" if image_model else "")
    db.commit()
    db.refresh(embedding)
    return embedding


def _handle_decision(
    db: Session,
    material: Material,
    analysis: AIAnalysis,
    best_candidate: Material | None,
    breakdown,
    decision_result,
) -> None:
    if decision_result.decision == Decision.AUTO_HARMONIZATION.value and best_candidate is not None:
        common_code = best_candidate.common_code
        if common_code is None:
            common_code = CommonMaterialCode(
                code=generate_common_code(
                    db,
                    material.material_type or best_candidate.material_type,
                    material.normalized_category or best_candidate.normalized_category,
                ),
                material_type=material.material_type or best_candidate.material_type or "GENERIC",
                category=material.normalized_category or best_candidate.normalized_category or material.category,
                standard_description=material.description,
                standard_specification=material.specification,
                uom=material.normalized_uom or material.uom,
                status="AUTO_GENERATED",
                created_by=None,
            )
            db.add(common_code)
            db.flush()
            best_candidate.common_code_id = common_code.id
            best_candidate.status = MaterialStatus.HARMONIZED.value

        material.common_code_id = common_code.id
        material.status = MaterialStatus.HARMONIZED.value

        harmonization = HarmonizationRequest(
            material_id=material.id,
            candidate_material_id=best_candidate.id,
            ai_analysis_id=analysis.id,
            requested_by=None,
            request_type="AI_AUTO",
            status=HarmonizationStatus.AUTO_APPROVED.value,
            common_code_id=common_code.id,
            notes="Automatically harmonized by AI - confidence met the auto-approval threshold.",
        )
        db.add(harmonization)
        analysis.recommended_common_code = common_code.code
        db.commit()

        log_action(
            db,
            action="AUTO_HARMONIZATION",
            entity_type="common_material_code",
            entity_id=common_code.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            details={
                "material_code": material.material_code,
                "candidate_code": best_candidate.material_code,
                "common_code": common_code.code,
                "final_score": breakdown.final_score,
            },
        )
        notify_role(
            db,
            RoleName.ADMIN.value,
            NotificationType.COMMON_CODE_GENERATED.value,
            "Common material code generated",
            f"{material.material_code} was auto-harmonized into {common_code.code} "
            f"with {breakdown.final_score:.1f}% AI confidence.",
            "common_material_code",
            common_code.id,
        )

    elif decision_result.decision == Decision.HUMAN_REVIEW_REQUIRED.value and best_candidate is not None:
        harmonization = HarmonizationRequest(
            material_id=material.id,
            candidate_material_id=best_candidate.id,
            ai_analysis_id=analysis.id,
            requested_by=None,
            request_type="AI_AUTO",
            status=HarmonizationStatus.PENDING.value,
        )
        db.add(harmonization)
        db.flush()

        approval = ApprovalRequest(
            harmonization_request_id=harmonization.id,
            material_id=material.id,
            candidate_material_id=best_candidate.id,
            ai_score=breakdown.final_score,
            status=ApprovalStatus.PENDING.value,
            reason=decision_result.reason_text,
        )
        db.add(approval)
        db.commit()

        log_action(
            db,
            action="APPROVAL_REQUEST_CREATED",
            entity_type="approval_request",
            entity_id=approval.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            details={"material_code": material.material_code, "final_score": breakdown.final_score},
        )
        notify_role(
            db,
            RoleName.MATERIAL_EXPERT.value,
            NotificationType.HUMAN_APPROVAL_REQUIRED.value,
            "Human approval required",
            f"{material.material_code} matched {best_candidate.material_code} at "
            f"{breakdown.final_score:.1f}% confidence - expert review required.",
            "approval_request",
            approval.id,
        )
    else:
        db.commit()


def analyze_material(db: Session, material_id: uuid.UUID) -> AIAnalysis:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise ValueError(f"Material {material_id} not found")

    material.status = MaterialStatus.PROCESSING.value
    db.commit()

    try:
        embedding = ensure_embeddings(db, material)
        candidates = find_candidate_materials(db, material)
        attrs_a = _attributes_dict(db, material.id)

        db.query(MaterialMatch).filter(MaterialMatch.material_id == material.id).delete()

        scored: list[tuple[Material, object]] = []
        for candidate in candidates:
            attrs_b = _attributes_dict(db, candidate.id)
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
            category_score_val = cat_score_fn(material.normalized_category or "", candidate.normalized_category or "")
            uom_score_val = uom_score_fn(material.normalized_uom or "", candidate.normalized_uom or "")
            attribute_score_val = attr_score_fn(attrs_a, attrs_b)

            has_image_both = (
                embedding.image_embedding is not None
                and cand_embedding is not None
                and cand_embedding.image_embedding is not None
            )
            image_score_val = (
                img_score_fn(embedding.image_embedding, cand_embedding.image_embedding)
                if has_image_both
                else 0.0
            )

            breakdown = compute_final_score(
                description_score,
                specification_score,
                category_score_val,
                uom_score_val,
                image_score_val,
                attribute_score_val,
                has_image_both,
            )

            db.add(
                MaterialMatch(
                    material_id=material.id,
                    candidate_material_id=candidate.id,
                    final_score=breakdown.final_score,
                    description_score=breakdown.description_score,
                    specification_score=breakdown.specification_score,
                    category_score=breakdown.category_score,
                    uom_score=breakdown.uom_score,
                    image_score=breakdown.image_score,
                    attribute_score=breakdown.attribute_score,
                    vector_distance=(1 - text_cos) if text_cos is not None else None,
                )
            )
            scored.append((candidate, breakdown))

        db.commit()

        if scored:
            best_candidate, best_breakdown = max(scored, key=lambda pair: pair[1].final_score)
        else:
            best_candidate, best_breakdown = None, compute_final_score(0, 0, 0, 0, 0, 0, False)

        decision_result = evaluate(
            best_breakdown, material.description, best_candidate.description if best_candidate else ""
        )
        failure_reason = "No similar material found in the database for comparison." if not scored else None

        analysis = AIAnalysis(
            material_id=material.id,
            best_candidate_material_id=best_candidate.id if best_candidate else None,
            final_score=best_breakdown.final_score,
            description_score=best_breakdown.description_score,
            specification_score=best_breakdown.specification_score,
            category_score=best_breakdown.category_score,
            uom_score=best_breakdown.uom_score,
            image_score=best_breakdown.image_score,
            attribute_score=best_breakdown.attribute_score,
            decision=decision_result.decision,
            reason_text=decision_result.reason_text if scored else decision_result.message,
            status="COMPLETED",
            failure_reason=failure_reason,
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
            entity_type="material",
            entity_id=material.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            details={
                "final_score": best_breakdown.final_score,
                "decision": decision_result.decision,
                "candidate": best_candidate.material_code if best_candidate else None,
            },
        )

        _handle_decision(db, material, analysis, best_candidate, best_breakdown, decision_result)

        if material.created_by:
            notify_user(
                db,
                material.created_by,
                NotificationType.AI_ANALYSIS_COMPLETED.value,
                "AI analysis completed",
                f"AI analysis for {material.material_code} finished with decision: {decision_result.decision}.",
                "material",
                material.id,
            )

        return analysis

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        material = db.query(Material).filter(Material.id == material_id).first()
        material.status = MaterialStatus.FAILED.value
        analysis = AIAnalysis(
            material_id=material.id,
            final_score=0,
            description_score=0,
            specification_score=0,
            category_score=0,
            uom_score=0,
            image_score=0,
            attribute_score=0,
            decision=Decision.NO_COMMON_CODE.value,
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
            entity_type="material",
            entity_id=material.id,
            actor_name="AI ENGINE",
            actor_type=ActorType.AI_ENGINE.value,
            details={"error": str(exc)},
        )
        if material.created_by:
            notify_user(
                db,
                material.created_by,
                NotificationType.AI_PROCESSING_FAILED.value,
                "AI processing failed",
                f"AI analysis for {material.material_code} failed: {exc}",
                "material",
                material.id,
            )
        logger.exception("AI analysis failed for material %s", material_id)
        return analysis
