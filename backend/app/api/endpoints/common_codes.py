import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.user import User
from app.schemas.harmonization import CommonMaterialDetailOut, CommonMaterialOut

router = APIRouter(prefix="/common-materials", tags=["Common Material Master"])

_NON_REJECTED = CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value


@router.get("", response_model=list[CommonMaterialOut])
def list_common_materials(
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(CommonMaterial)
    if cpse_id:
        mapped_ids = (
            db.query(CommonMaterialMapping.common_material_id)
            .join(CPSEMaterial, CommonMaterialMapping.cpse_material_id == CPSEMaterial.id)
            .filter(CPSEMaterial.cpse_id == cpse_id, _NON_REJECTED)
        )
        query = query.filter(CommonMaterial.id.in_(mapped_ids))
    return query.order_by(CommonMaterial.created_at.desc()).all()


@router.get("/{code}", response_model=CommonMaterialDetailOut)
def get_common_material(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    common_material = db.query(CommonMaterial).filter(CommonMaterial.common_code == code).first()
    if not common_material:
        raise HTTPException(status_code=404, detail="Common material not found")

    mappings = (
        db.query(CommonMaterialMapping)
        .filter(CommonMaterialMapping.common_material_id == common_material.id, _NON_REJECTED)
        .all()
    )
    mapped_materials = [m.cpse_material for m in mappings]
    mapped_cpses = sorted({m.cpse.code for m in mapped_materials if m.cpse})

    out = CommonMaterialDetailOut.model_validate(common_material)
    out.mapped_materials = mapped_materials
    out.mapped_cpses = mapped_cpses
    return out
