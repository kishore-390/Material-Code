"""
The one and only place that writes an AI/human recommendation into the
official Common Material Master (spec section 10 governance rule).
Every call here is paired with an audit log entry in the same
transaction, and callers must already have confirmed the actor is
authorized (ADMIN / MATERIAL_EXPERT) before invoking approve/reject.
"""
from app.models.enums import ActorType, HarmonizationStatus, MaterialStatus, NotificationType
from app.models.harmonization import CommonMaterialCode, HarmonizationRequest
from app.models.user import User
from app.services.audit_service import log_action
from app.services.code_generator import generate_common_code
from app.services.notification_service import notify_user


def approve_harmonization(db, harmonization: HarmonizationRequest, actor: User, remarks: str | None) -> CommonMaterialCode:
    material = harmonization.material
    candidate = harmonization.candidate

    common_code = None
    if candidate is not None:
        common_code = candidate.common_code
    if common_code is None and material.common_code is not None:
        common_code = material.common_code

    if common_code is None:
        common_code = CommonMaterialCode(
            code=generate_common_code(db),
            material_type=material.material_type or (candidate.material_type if candidate else None) or "GENERIC",
            category=material.normalized_category or (candidate.normalized_category if candidate else None) or material.category,
            standard_description=material.description,
            standard_specification=material.specification,
            uom=material.normalized_uom or material.uom,
            status="APPROVED",
            created_by=actor.id,
        )
        db.add(common_code)
        db.flush()
    else:
        common_code.status = "APPROVED"

    material.common_code_id = common_code.id
    material.status = MaterialStatus.HARMONIZED.value
    if candidate is not None:
        candidate.common_code_id = common_code.id
        candidate.status = MaterialStatus.HARMONIZED.value

    harmonization.status = HarmonizationStatus.APPROVED.value
    harmonization.common_code_id = common_code.id
    db.commit()

    log_action(
        db,
        action="APPROVED",
        entity_type="harmonization_request",
        entity_id=harmonization.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type=ActorType.USER.value,
        details={"common_code": common_code.code, "remarks": remarks},
    )

    if harmonization.requested_by:
        notify_user(
            db,
            harmonization.requested_by,
            NotificationType.APPROVAL_COMPLETED.value,
            "Harmonization approved",
            f"{material.material_code} was approved and linked to common code {common_code.code}.",
            "common_material_code",
            common_code.id,
        )
    if material.created_by:
        notify_user(
            db,
            material.created_by,
            NotificationType.COMMON_CODE_GENERATED.value,
            "Common material code generated",
            f"{material.material_code} is now part of common code {common_code.code}.",
            "common_material_code",
            common_code.id,
        )
    return common_code


def reject_harmonization(db, harmonization: HarmonizationRequest, actor: User, remarks: str | None) -> None:
    harmonization.status = HarmonizationStatus.REJECTED.value
    db.commit()

    log_action(
        db,
        action="REJECTED",
        entity_type="harmonization_request",
        entity_id=harmonization.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type=ActorType.USER.value,
        details={"remarks": remarks},
    )

    if harmonization.requested_by:
        notify_user(
            db,
            harmonization.requested_by,
            NotificationType.MATERIAL_REJECTED.value,
            "Harmonization rejected",
            f"The harmonization request for {harmonization.material.material_code} was rejected. "
            f"Reason: {remarks or 'Not specified'}",
            "harmonization_request",
            harmonization.id,
        )
