import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.cpse import CPSE
from app.models.enums import MappingDecisionStatus, MappingType
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.source_connection import SourceConnection
from app.models.user import User
from app.schemas.dashboard import ChartPoint, DashboardStatistics, DashboardTrends
from app.services.duplicate_service import count_duplicate_materials

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_NON_REJECTED = CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value
_PENDING_STATUSES = (
    MappingDecisionStatus.AI_RECOMMENDED.value,
    MappingDecisionStatus.PENDING_VALIDATION.value,
    MappingDecisionStatus.MANUAL_REVIEW.value,
)


@router.get("/statistics", response_model=DashboardStatistics)
def get_statistics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cpses_connected = db.query(func.count(CPSE.id)).filter(CPSE.is_active.is_(True)).scalar() or 0
    total_materials = db.query(func.count(CPSEMaterial.id)).scalar() or 0
    common_material_codes = db.query(func.count(CommonMaterial.id)).scalar() or 0

    duplicates_identified = (
        db.query(func.count(CommonMaterialMapping.id))
        .filter(_NON_REJECTED, CommonMaterialMapping.mapping_type.in_([MappingType.IDENTICAL.value, MappingType.DUPLICATE.value]))
        .scalar()
        or 0
    )
    near_duplicates = (
        db.query(func.count(CommonMaterialMapping.id))
        .filter(_NON_REJECTED, CommonMaterialMapping.mapping_type == MappingType.NEAR_DUPLICATE.value)
        .scalar()
        or 0
    )
    functionally_equivalent = (
        db.query(func.count(CommonMaterialMapping.id))
        .filter(_NON_REJECTED, CommonMaterialMapping.mapping_type == MappingType.FUNCTIONALLY_EQUIVALENT.value)
        .scalar()
        or 0
    )
    pending_validation = (
        db.query(func.count(CommonMaterialMapping.id))
        .filter(CommonMaterialMapping.decision_status.in_(_PENDING_STATUSES))
        .scalar()
        or 0
    )
    technical_conflicts = (
        db.query(func.count(CommonMaterialMapping.id))
        .filter(CommonMaterialMapping.decision_status == MappingDecisionStatus.TECHNICAL_CONFLICT.value)
        .scalar()
        or 0
    )
    legacy_codes_rationalized = (
        db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.is_active.is_(False)).scalar() or 0
    )

    from app.services.procurement_service import estimate_total_aggregation_value

    potential_aggregation_value = estimate_total_aggregation_value(db)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    new_materials_today = (
        db.query(func.count(CPSEMaterial.id)).filter(CPSEMaterial.created_at >= today_start).scalar() or 0
    )
    last_synchronization = db.query(func.max(SourceConnection.last_successful_sync)).scalar()

    return DashboardStatistics(
        cpses_connected=cpses_connected,
        total_materials=total_materials,
        common_material_codes=common_material_codes,
        duplicates_identified=duplicates_identified,
        near_duplicates=near_duplicates,
        functionally_equivalent=functionally_equivalent,
        pending_validation=pending_validation,
        legacy_codes_rationalized=legacy_codes_rationalized,
        potential_procurement_aggregation_value=potential_aggregation_value,
        technical_conflicts=technical_conflicts,
        new_materials_today=new_materials_today,
        last_synchronization=last_synchronization,
    )


@router.get("/trends", response_model=DashboardTrends)
def get_trends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    materials_by_cpse_rows = (
        db.query(CPSE.code, func.count(CPSEMaterial.id))
        .join(CPSEMaterial, CPSEMaterial.cpse_id == CPSE.id)
        .group_by(CPSE.code)
        .all()
    )
    materials_by_cpse = [ChartPoint(label=code, value=count) for code, count in materials_by_cpse_rows]

    dup_by_common_material = (
        db.query(CommonMaterialMapping.common_material_id, func.count(CommonMaterialMapping.id))
        .filter(_NON_REJECTED)
        .group_by(CommonMaterialMapping.common_material_id)
        .all()
    )
    duplicate_reduction = [
        ChartPoint(label=str(i + 1), value=max(count - 1, 0)) for i, (_, count) in enumerate(dup_by_common_material)
    ]

    status_rows = (
        db.query(CommonMaterialMapping.decision_status, func.count(CommonMaterialMapping.id))
        .filter(_NON_REJECTED)
        .group_by(CommonMaterialMapping.decision_status)
        .all()
    )
    common_code_adoption = [ChartPoint(label=status, value=count) for status, count in status_rows]

    harmonized = db.query(func.count(func.distinct(CommonMaterialMapping.cpse_material_id))).filter(_NON_REJECTED).scalar() or 0
    total = db.query(func.count(CPSEMaterial.id)).scalar() or 0
    harmonization_progress = [
        ChartPoint(label="Mapped", value=harmonized),
        ChartPoint(label="Unmapped", value=max(total - harmonized, 0)),
    ]

    cpse_contribution = materials_by_cpse

    from app.services.procurement_service import list_collaborative_opportunities

    opportunities = list_collaborative_opportunities(db, limit=10)
    procurement_aggregation_opportunities = [
        ChartPoint(label=o.common_code, value=o.total_potential_aggregated_demand) for o in opportunities
    ]

    return DashboardTrends(
        materials_by_cpse=materials_by_cpse,
        duplicate_reduction=duplicate_reduction,
        common_code_adoption=common_code_adoption,
        harmonization_progress=harmonization_progress,
        cpse_contribution=cpse_contribution,
        procurement_aggregation_opportunities=procurement_aggregation_opportunities,
    )
