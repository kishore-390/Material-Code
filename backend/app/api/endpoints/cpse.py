import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.approval import ApprovalRequest
from app.models.cpse import CPSEOrganization
from app.models.enums import ApprovalStatus, MaterialStatus, RoleName
from app.models.material import Material
from app.models.user import User
from app.schemas.cpse import CPSECreate, CPSEOut, CPSEStats

router = APIRouter(prefix="/cpse", tags=["CPSE Directory"])


def _stats_for(db: Session, cpse: CPSEOrganization) -> CPSEStats:
    total = db.query(func.count(Material.id)).filter(Material.cpse_id == cpse.id).scalar() or 0
    harmonized = (
        db.query(func.count(Material.id))
        .filter(Material.cpse_id == cpse.id, Material.status == MaterialStatus.HARMONIZED.value)
        .scalar()
        or 0
    )
    common_codes = (
        db.query(func.count(func.distinct(Material.common_code_id)))
        .filter(Material.cpse_id == cpse.id, Material.common_code_id.isnot(None))
        .scalar()
        or 0
    )
    pending_approvals = (
        db.query(func.count(ApprovalRequest.id))
        .join(Material, ApprovalRequest.material_id == Material.id)
        .filter(Material.cpse_id == cpse.id, ApprovalRequest.status == ApprovalStatus.PENDING.value)
        .scalar()
        or 0
    )
    duplicate_groups = (
        db.query(Material.common_code_id)
        .filter(Material.cpse_id == cpse.id, Material.common_code_id.isnot(None))
        .group_by(Material.common_code_id)
        .having(func.count(Material.id) > 1)
        .count()
    )
    percentage = round((harmonized / total) * 100, 1) if total else 0.0

    return CPSEStats(
        id=cpse.id,
        code=cpse.code,
        name=cpse.name,
        sector=cpse.sector,
        is_active=cpse.is_active,
        created_at=cpse.created_at,
        total_materials=total,
        harmonized_materials=harmonized,
        pending_approvals=pending_approvals,
        common_codes=common_codes,
        duplicate_materials=duplicate_groups,
        harmonization_percentage=percentage,
    )


@router.get("", response_model=list[CPSEStats])
def list_cpse(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    orgs = db.query(CPSEOrganization).order_by(CPSEOrganization.name).all()
    return [_stats_for(db, org) for org in orgs]


@router.post("", response_model=CPSEOut, status_code=201)
def create_cpse(
    payload: CPSECreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    if db.query(CPSEOrganization).filter(CPSEOrganization.code == payload.code.upper()).first():
        raise HTTPException(status_code=400, detail="CPSE code already exists")
    cpse = CPSEOrganization(code=payload.code.upper(), name=payload.name, sector=payload.sector)
    db.add(cpse)
    db.commit()
    db.refresh(cpse)
    return cpse


@router.get("/{cpse_id}", response_model=CPSEStats)
def get_cpse(cpse_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cpse = db.query(CPSEOrganization).filter(CPSEOrganization.id == cpse_id).first()
    if not cpse:
        raise HTTPException(status_code=404, detail="CPSE not found")
    return _stats_for(db, cpse)
