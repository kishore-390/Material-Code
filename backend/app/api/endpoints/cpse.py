import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.approval import ApprovalRequest
from app.models.cpse import CPSEOrganization
from app.models.enums import ApprovalStatus, MaterialStatus, RoleName
from app.models.material import Material
from app.models.upload_batch import UploadBatch
from app.models.user import User
from app.schemas.cpse import CPSEOut, CPSEStats, CPSEStatusUpdate
from app.schemas.upload import UploadBatchListResponse
from app.services.file_storage import ALLOWED_IMAGE_EXTENSIONS, save_upload

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
        description=cpse.description,
        logo_url=cpse.logo_url,
        is_active=cpse.is_active,
        created_at=cpse.created_at,
        total_materials=total,
        harmonized_materials=harmonized,
        pending_approvals=pending_approvals,
        common_codes=common_codes,
        duplicate_materials=duplicate_groups,
        harmonization_percentage=percentage,
    )


def _get_or_404(db: Session, cpse_id: uuid.UUID) -> CPSEOrganization:
    cpse = db.query(CPSEOrganization).filter(CPSEOrganization.id == cpse_id).first()
    if not cpse:
        raise HTTPException(status_code=404, detail="CPSE not found")
    return cpse


@router.get("", response_model=list[CPSEStats])
def list_cpse(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    orgs = db.query(CPSEOrganization).order_by(CPSEOrganization.name).all()
    return [_stats_for(db, org) for org in orgs]


@router.post("", response_model=CPSEOut, status_code=201)
def create_cpse(
    code: str = Form(...),
    name: str = Form(...),
    sector: str | None = Form(None),
    description: str | None = Form(None),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    if db.query(CPSEOrganization).filter(CPSEOrganization.code == code.upper()).first():
        raise HTTPException(status_code=400, detail="CPSE code already exists")

    logo_url = None
    if logo is not None and logo.filename:
        try:
            logo_url = save_upload(logo, "organizations", ALLOWED_IMAGE_EXTENSIONS)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    cpse = CPSEOrganization(
        code=code.upper(), name=name, sector=sector, description=description, logo_url=logo_url
    )
    db.add(cpse)
    db.commit()
    db.refresh(cpse)
    return cpse


@router.get("/{cpse_id}", response_model=CPSEStats)
def get_cpse(cpse_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _stats_for(db, _get_or_404(db, cpse_id))


@router.get("/{cpse_id}/statistics", response_model=CPSEStats)
def get_cpse_statistics(
    cpse_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _stats_for(db, _get_or_404(db, cpse_id))


@router.put("/{cpse_id}", response_model=CPSEOut)
def update_cpse(
    cpse_id: uuid.UUID,
    name: str | None = Form(None),
    sector: str | None = Form(None),
    description: str | None = Form(None),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    cpse = _get_or_404(db, cpse_id)

    if name is not None:
        cpse.name = name
    if sector is not None:
        cpse.sector = sector
    if description is not None:
        cpse.description = description
    if logo is not None and logo.filename:
        try:
            cpse.logo_url = save_upload(logo, "organizations", ALLOWED_IMAGE_EXTENSIONS)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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


@router.get("/{cpse_id}/uploads", response_model=UploadBatchListResponse)
def list_cpse_uploads(
    cpse_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_or_404(db, cpse_id)
    if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id != cpse_id:
        raise HTTPException(status_code=403, detail="You may only view your own CPSE's upload history")

    query = db.query(UploadBatch).filter(UploadBatch.cpse_id == cpse_id)
    total = query.count()
    items = (
        query.order_by(UploadBatch.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return UploadBatchListResponse(items=items, total=total, page=page, page_size=page_size)
