"""
The one and only place that moves a CommonMaterialMapping into an official,
governance-approved state (spec section 10/14 governance rule). Every call
here is paired with an audit log entry in the same transaction, and callers
must already have confirmed the actor is authorized (ADMIN /
MATERIAL_EXPERT) before invoking these.
"""
from app.models.approval import ApprovalAction
from app.models.enums import ApprovalActionType, MappingDecisionStatus, MaterialStatus, NotificationType
from app.models.harmonization import CommonMaterialMapping
from app.models.user import User
from app.services.audit_service import log_action
from app.services.notification_service import notify_role


def _snapshot(mapping: CommonMaterialMapping) -> dict:
    return {
        "mapping_type": mapping.mapping_type,
        "decision_status": mapping.decision_status,
        "common_code": mapping.common_material.common_code,
    }


def approve_mapping(db, mapping: CommonMaterialMapping, actor: User, remarks: str | None) -> CommonMaterialMapping:
    before = _snapshot(mapping)
    mapping.decision_status = MappingDecisionStatus.APPROVED.value
    mapping.approved_by = actor.id
    from datetime import datetime, timezone

    mapping.approved_at = datetime.now(timezone.utc)
    mapping.cpse_material.status = MaterialStatus.HARMONIZED.value
    db.add(ApprovalAction(mapping_id=mapping.id, action=ApprovalActionType.APPROVE.value, actor_id=actor.id, remarks=remarks))
    db.commit()

    log_action(
        db,
        action="MAPPING_APPROVED",
        entity_type="common_material_mapping",
        entity_id=mapping.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type="USER",
        before_state=before,
        after_state=_snapshot(mapping),
        reason=remarks,
    )
    notify_role(
        db,
        "VIEWER",
        NotificationType.APPROVAL_COMPLETED.value,
        "Mapping approved",
        f"{mapping.cpse_material.original_material_code} was approved and linked to common code {mapping.common_material.common_code}.",
        "common_material_mapping",
        mapping.id,
    )
    return mapping


def reject_mapping(db, mapping: CommonMaterialMapping, actor: User, remarks: str | None) -> CommonMaterialMapping:
    before = _snapshot(mapping)
    mapping.decision_status = MappingDecisionStatus.REJECTED.value
    db.add(ApprovalAction(mapping_id=mapping.id, action=ApprovalActionType.REJECT.value, actor_id=actor.id, remarks=remarks))
    db.commit()

    log_action(
        db,
        action="MAPPING_REJECTED",
        entity_type="common_material_mapping",
        entity_id=mapping.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type="USER",
        before_state=before,
        after_state=_snapshot(mapping),
        reason=remarks,
    )
    notify_role(
        db,
        "VIEWER",
        NotificationType.MAPPING_REJECTED.value,
        "Mapping rejected",
        f"The proposed mapping for {mapping.cpse_material.original_material_code} was rejected. Reason: {remarks or 'Not specified'}",
        "common_material_mapping",
        mapping.id,
    )
    return mapping


def edit_and_approve_mapping(
    db, mapping: CommonMaterialMapping, actor: User, remarks: str | None, standardized_fields: dict
) -> CommonMaterialMapping:
    """A Material Expert corrects the AI's standardized representation
    before approving (spec section 14/22 'Edit & Approve')."""
    before = _snapshot(mapping)
    common_material = mapping.common_material
    for field, value in standardized_fields.items():
        if hasattr(common_material, field) and value is not None:
            setattr(common_material, field, value)

    mapping.decision_status = MappingDecisionStatus.EDITED_AND_APPROVED.value
    mapping.approved_by = actor.id
    from datetime import datetime, timezone

    mapping.approved_at = datetime.now(timezone.utc)
    mapping.cpse_material.status = MaterialStatus.HARMONIZED.value
    db.add(
        ApprovalAction(mapping_id=mapping.id, action=ApprovalActionType.EDIT_AND_APPROVE.value, actor_id=actor.id, remarks=remarks)
    )
    db.commit()

    log_action(
        db,
        action="MAPPING_EDITED_AND_APPROVED",
        entity_type="common_material_mapping",
        entity_id=mapping.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type="USER",
        before_state=before,
        after_state=_snapshot(mapping),
        reason=remarks,
    )
    return mapping


def send_to_manual_review(db, mapping: CommonMaterialMapping, actor: User, remarks: str | None) -> CommonMaterialMapping:
    before = _snapshot(mapping)
    mapping.decision_status = MappingDecisionStatus.MANUAL_REVIEW.value
    db.add(
        ApprovalAction(mapping_id=mapping.id, action=ApprovalActionType.MANUAL_REVIEW.value, actor_id=actor.id, remarks=remarks)
    )
    db.commit()

    log_action(
        db,
        action="MAPPING_SENT_TO_MANUAL_REVIEW",
        entity_type="common_material_mapping",
        entity_id=mapping.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type="USER",
        before_state=before,
        after_state=_snapshot(mapping),
        reason=remarks,
    )
    return mapping


def request_more_info(db, mapping: CommonMaterialMapping, actor: User, remarks: str | None) -> CommonMaterialMapping:
    db.add(
        ApprovalAction(
            mapping_id=mapping.id, action=ApprovalActionType.REQUEST_MORE_INFO.value, actor_id=actor.id, remarks=remarks
        )
    )
    db.commit()

    log_action(
        db,
        action="MAPPING_MORE_INFO_REQUESTED",
        entity_type="common_material_mapping",
        entity_id=mapping.id,
        actor_id=actor.id,
        actor_name=actor.full_name,
        actor_type="USER",
        reason=remarks,
    )
    return mapping
