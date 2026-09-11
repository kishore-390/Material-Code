"""spec section 24 - deeper analytics beyond the dashboard's headline KPIs."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.cpse import CPSE
from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.user import User
from app.schemas.dashboard import ChartPoint

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_NON_REJECTED = CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value


@router.get("/classification-distribution", response_model=list[ChartPoint])
def classification_distribution(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(CPSEMaterial.classification, func.count(CPSEMaterial.id))
        .group_by(CPSEMaterial.classification)
        .order_by(func.count(CPSEMaterial.id).desc())
        .limit(20)
        .all()
    )
    return [ChartPoint(label=c or "Unclassified", value=v) for c, v in rows]


@router.get("/cpse-comparison", response_model=list[ChartPoint])
def cpse_comparison(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(CPSE.code, func.count(CPSEMaterial.id))
        .join(CPSEMaterial, CPSEMaterial.cpse_id == CPSE.id)
        .group_by(CPSE.code)
        .all()
    )
    return [ChartPoint(label=c, value=v) for c, v in rows]


@router.get("/common-code-adoption", response_model=list[ChartPoint])
def common_code_adoption(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(CommonMaterial.status, func.count(CommonMaterial.id))
        .group_by(CommonMaterial.status)
        .all()
    )
    return [ChartPoint(label=s, value=v) for s, v in rows]


@router.get("/material-quality", response_model=list[ChartPoint])
def material_quality(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """spec section 32 - missing critical attribute counts."""
    total = db.query(func.count(CPSEMaterial.id)).scalar() or 0
    missing_grade = db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.material_grade.is_(None)).scalar() or 0
    missing_dimensions = db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.dimensions.is_(None)).scalar() or 0
    missing_spec = db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.technical_specification.is_(None)).scalar() or 0
    missing_manufacturer = db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.manufacturer.is_(None)).scalar() or 0
    return [
        ChartPoint(label="Total materials", value=total),
        ChartPoint(label="Missing grade", value=missing_grade),
        ChartPoint(label="Missing dimensions", value=missing_dimensions),
        ChartPoint(label="Missing specification", value=missing_spec),
        ChartPoint(label="Missing manufacturer", value=missing_manufacturer),
    ]


@router.get("/harmonization-trends", response_model=list[ChartPoint])
def harmonization_trends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(func.to_char(CommonMaterialMapping.created_at, "YYYY-MM").label("month"), func.count(CommonMaterialMapping.id))
        .filter(_NON_REJECTED)
        .group_by("month")
        .order_by("month")
        .all()
    )
    return [ChartPoint(label=month, value=count) for month, count in rows]
