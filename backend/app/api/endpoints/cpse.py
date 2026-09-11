import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import assert_cpse_access, get_current_user, require_roles
from app.db.session import get_db
from app.models.cpse import CPSE
from app.models.enums import MappingDecisionStatus, MappingType, RoleName
from app.models.harmonization import CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.user import User
from app.schemas.cpse import CPSECreate, CPSEOut, CPSEStats, CPSEStatusUpdate, CPSEUpdate

router = APIRouter(prefix="/cpse", tags=["CPSE Network"])

_NON_REJECTED = CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value
_PENDING_STATUSES = (
    MappingDecisionStatus.AI_RECOMMENDED.value,
    MappingDecisionStatus.PENDING_VALIDATION.value,
    MappingDecisionStatus.MANUAL_REVIEW.value,
)


def _stats_for(db: Session, cpse: CPSE) -> CPSEStats:
    total = db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.cpse_id == cpse.id).scalar() or 0

    mapping_rows = (
        db.query(CommonMaterialMapping.mapping_type, CommonMaterialMapping.decision_status)
        .join(CPSEMaterial, CommonMaterialMapping.cpse_material_id == CPSEMaterial.id)
        .filter(CPSEMaterial.cpse_id == cpse.id, _NON_REJECTED)
        .all()
    )
    common_materials = len(mapping_rows)
    duplicates = sum(1 for mt, _ in mapping_rows if mt in (MappingType.IDENTICAL.value, MappingType.DUPLICATE.value))
    near_duplicates = sum(1 for mt, _ in mapping_rows if mt == MappingType.NEAR_DUPLICATE.value)
    functional_equivalents = sum(1 for mt, _ in mapping_rows if mt == MappingType.FUNCTIONALLY_EQUIVALENT.value)
    pending_mappings = sum(1 for _, ds in mapping_rows if ds in _PENDING_STATUSES)
    unique_materials = total - common_materials

    legacy_codes = (
        db.query(func.count(func.distinct(CPSEMaterial.original_material_code)))
        .filter(CPSEMaterial.cpse_id == cpse.id, CPSEMaterial.is_active.is_(False))
        .scalar()
        or 0
    )

    return CPSEStats(
        id=cpse.id,
        code=cpse.code,
        name=cpse.name,
        sector=cpse.sector,
        description=cpse.description,
        logo_url=cpse.logo_url,
        is_active=cpse.is_active,
        last_sync_at=cpse.last_sync_at,
        synchronization_status=cpse.synchronization_status,
        created_at=cpse.created_at,
        total_materials=total,
        common_materials=common_materials,
        unique_materials=max(unique_materials, 0),
        duplicates=duplicates,
        near_duplicates=near_duplicates,
        functional_equivalents=functional_equivalents,
        pending_mappings=pending_mappings,
        legacy_codes=legacy_codes,
    )


def _get_or_404(db: Session, cpse_id: uuid.UUID) -> CPSE:
    cpse = db.query(CPSE).filter(CPSE.id == cpse_id).first()
    if not cpse:
        raise HTTPException(status_code=404, detail="CPSE not found")
    return cpse


@router.get("", response_model=list[CPSEStats])
def list_cpse(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """A company-scoped user only ever sees their own company's row here -
    "Each company should only be able to access its own material database"
    applies to the CPSE roster too, not just the materials underneath it."""
    query = db.query(CPSE)
    if current_user.cpse_id is not None:
        query = query.filter(CPSE.id == current_user.cpse_id)
    cpses = query.order_by(CPSE.name).all()
    return [_stats_for(db, c) for c in cpses]


@router.post("", response_model=CPSEOut, status_code=201)
def create_cpse(
    payload: CPSECreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    if db.query(CPSE).filter(CPSE.code == payload.code.upper()).first():
        raise HTTPException(status_code=400, detail="CPSE code already exists")

    cpse = CPSE(code=payload.code.upper(), name=payload.name, sector=payload.sector, description=payload.description)
    db.add(cpse)
    db.commit()
    db.refresh(cpse)
    return cpse


@router.get("/{cpse_id}", response_model=CPSEStats)
def get_cpse(cpse_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_cpse_access(current_user, cpse_id)
    return _stats_for(db, _get_or_404(db, cpse_id))


@router.put("/{cpse_id}", response_model=CPSEOut)
def update_cpse(
    cpse_id: uuid.UUID,
    payload: CPSEUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    cpse = _get_or_404(db, cpse_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cpse, field, value)
    db.commit()
    db.refresh(cpse)
    return cpse


@router.patch("/{cpse_id}/status", response_model=CPSEOut)
def set_cpse_status(
    cpse_id: uuid.UUID,
    payload: CPSEStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    cpse = _get_or_404(db, cpse_id)
    cpse.is_active = payload.is_active
    db.commit()
    db.refresh(cpse)
    return cpse
