import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import MappingDecisionStatus, MappingType, RoleName
from app.models.harmonization import CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.user import User
from app.schemas.approval import ApprovalActionRequest, ApprovalDetailOut, EditAndApproveRequest
from app.schemas.harmonization import MappingOut
from app.services.harmonization_service import (
    approve_mapping,
    edit_and_approve_mapping,
    reject_mapping,
    request_more_info,
    send_to_manual_review,
)

router = APIRouter(prefix="/approvals", tags=["Approvals"])

_REVIEW_ROLES = (RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value, RoleName.VIEWER.value, RoleName.REVIEWER.value)
_ACT_ROLES = (RoleName.ADMIN.value, RoleName.MATERIAL_EXPERT.value)


def _get_or_404(db: Session, mapping_id: uuid.UUID) -> CommonMaterialMapping:
    mapping = db.query(CommonMaterialMapping).filter(CommonMaterialMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.get("/pending", response_model=list[MappingOut])
def list_pending(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_REVIEW_ROLES)),
):
    return (
        db.query(CommonMaterialMapping)
        .filter(
            CommonMaterialMapping.decision_status.in_(
                [
                    MappingDecisionStatus.AI_RECOMMENDED.value,
                    MappingDecisionStatus.PENDING_VALIDATION.value,
                    MappingDecisionStatus.MANUAL_REVIEW.value,
                    MappingDecisionStatus.TECHNICAL_CONFLICT.value,
                ]
            )
        )
        .order_by(CommonMaterialMapping.created_at.desc())
        .all()
    )


@router.get("/approved", response_model=list[MappingOut])
def list_approved(db: Session = Depends(get_db), current_user: User = Depends(require_roles(*_REVIEW_ROLES))):
    return (
        db.query(CommonMaterialMapping)
        .filter(
            CommonMaterialMapping.decision_status.in_(
                [MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value]
            )
        )
        .order_by(CommonMaterialMapping.updated_at.desc())
        .all()
    )


@router.get("/rejected", response_model=list[MappingOut])
def list_rejected(db: Session = Depends(get_db), current_user: User = Depends(require_roles(*_REVIEW_ROLES))):
    return (
        db.query(CommonMaterialMapping)
        .filter(CommonMaterialMapping.decision_status == MappingDecisionStatus.REJECTED.value)
        .order_by(CommonMaterialMapping.updated_at.desc())
        .all()
    )


@router.get("/{mapping_id}", response_model=ApprovalDetailOut)
def get_mapping(mapping_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(*_REVIEW_ROLES))):
    mapping = _get_or_404(db, mapping_id)
    out = ApprovalDetailOut.model_validate(mapping)
    out.actions = mapping.actions
    return out


@router.post("/{mapping_id}/approve", response_model=MappingOut)
def approve(
    mapping_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ACT_ROLES)),
):
    mapping = _get_or_404(db, mapping_id)
    if mapping.decision_status in (MappingDecisionStatus.APPROVED.value, MappingDecisionStatus.EDITED_AND_APPROVED.value):
        raise HTTPException(status_code=400, detail="This mapping has already been approved")
    return approve_mapping(db, mapping, current_user, payload.remarks)


@router.post("/{mapping_id}/reject", response_model=MappingOut)
def reject(
    mapping_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ACT_ROLES)),
):
    mapping = _get_or_404(db, mapping_id)
    return reject_mapping(db, mapping, current_user, payload.remarks)


@router.post("/{mapping_id}/edit-and-approve", response_model=MappingOut)
def edit_and_approve(
    mapping_id: uuid.UUID,
    payload: EditAndApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ACT_ROLES)),
):
    mapping = _get_or_404(db, mapping_id)
    fields = payload.model_dump(exclude={"remarks"}, exclude_unset=True)
    return edit_and_approve_mapping(db, mapping, current_user, payload.remarks, fields)


@router.post("/{mapping_id}/manual-review", response_model=MappingOut)
def manual_review(
    mapping_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ACT_ROLES)),
):
    mapping = _get_or_404(db, mapping_id)
    return send_to_manual_review(db, mapping, current_user, payload.remarks)


@router.post("/{mapping_id}/request-more-info", response_model=MappingOut)
def more_info(
    mapping_id: uuid.UUID,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ACT_ROLES)),
):
    mapping = _get_or_404(db, mapping_id)
    return request_more_info(db, mapping, current_user, payload.remarks)


@router.post("/manual", response_model=MappingOut, status_code=201)
def create_manual_mapping(
    cpse_material_id: uuid.UUID = Body(...),
    matched_against_material_id: uuid.UUID = Body(...),
    remarks: str | None = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ACT_ROLES)),
):
    """
    A Material Expert manually links two ALREADY-SYNCED CPSE materials as
    the same underlying item (spec section 5.4 MANUAL_MAPPING) - this never
    creates a new material record, only a relationship between two that
    already exist via automatic synchronization.
    """
    from app.models.harmonization import CommonMaterial
    from app.services.code_generator import generate_common_code

    material = db.query(CPSEMaterial).filter(CPSEMaterial.id == cpse_material_id).first()
    candidate = db.query(CPSEMaterial).filter(CPSEMaterial.id == matched_against_material_id).first()
    if not material or not candidate:
        raise HTTPException(status_code=404, detail="One or both CPSE materials were not found")

    common_material = CommonMaterial(
        common_code=generate_common_code(db),
        material_type=material.material_type or "GENERIC",
        classification=material.normalized_classification or material.classification or "UNCLASSIFIED",
        standardized_description=material.original_description,
        standardized_specification=material.technical_specification,
        material_grade=material.material_grade,
        dimensions=material.dimensions,
        standardized_uom=material.normalized_uom or material.uom,
        standard=material.standard,
        function=material.function,
        criticality=material.criticality,
    )
    db.add(common_material)
    db.flush()

    mapping = CommonMaterialMapping(
        common_material_id=common_material.id,
        cpse_material_id=material.id,
        matched_against_material_id=candidate.id,
        mapping_type=MappingType.MANUAL_MAPPING.value,
        decision_status=MappingDecisionStatus.PENDING_VALIDATION.value,
        reason=remarks or "Manually proposed mapping.",
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping
