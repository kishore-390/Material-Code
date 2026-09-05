import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.approval import ApprovalRequest
from app.models.cpse import CPSEOrganization
from app.models.enums import ApprovalStatus, MaterialStatus
from app.models.harmonization import CommonMaterialCode
from app.models.matching import AIAnalysis
from app.models.material import Material
from app.models.user import User
from app.schemas.dashboard import ChartPoint, DashboardStatistics, DashboardTrends

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

ESTIMATED_SAVING_PER_DUPLICATE_INR = 45000


def _duplicate_codes_reduced(db: Session) -> int:
    subq = (
        db.query(Material.common_code_id, func.count(Material.id).label("cnt"))
        .filter(Material.common_code_id.isnot(None))
        .group_by(Material.common_code_id)
        .subquery()
    )
    total_extra = db.query(func.coalesce(func.sum(subq.c.cnt - 1), 0)).scalar() or 0
    return int(total_extra)


@router.get("/statistics", response_model=DashboardStatistics)
def get_statistics(
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    material_query = db.query(func.count(Material.id))
    harmonized_query = db.query(func.count(Material.id)).filter(Material.status == MaterialStatus.HARMONIZED.value)
    approvals_query = (
        db.query(func.count(ApprovalRequest.id))
        .join(Material, ApprovalRequest.material_id == Material.id)
        .filter(ApprovalRequest.status == ApprovalStatus.PENDING.value)
    )
    ai_query = db.query(func.count(AIAnalysis.id)).join(Material, AIAnalysis.material_id == Material.id)
    common_codes_query = db.query(func.count(func.distinct(Material.common_code_id))).filter(
        Material.common_code_id.isnot(None)
    )
    approved_codes_query = db.query(func.count(CommonMaterialCode.id)).filter(
        CommonMaterialCode.status == "APPROVED"
    )

    if cpse_id:
        material_query = material_query.filter(Material.cpse_id == cpse_id)
        harmonized_query = harmonized_query.filter(Material.cpse_id == cpse_id)
        approvals_query = approvals_query.filter(Material.cpse_id == cpse_id)
        ai_query = ai_query.filter(Material.cpse_id == cpse_id)
        common_codes_query = common_codes_query.filter(Material.cpse_id == cpse_id)
        approved_codes_query = approved_codes_query.filter(
            CommonMaterialCode.id.in_(
                db.query(Material.common_code_id).filter(
                    Material.cpse_id == cpse_id, Material.common_code_id.isnot(None)
                )
            )
        )

    total_materials = material_query.scalar() or 0
    harmonized_materials = harmonized_query.scalar() or 0
    pending_human_approvals = approvals_query.scalar() or 0
    cpses_onboarded = db.query(func.count(CPSEOrganization.id)).scalar() or 0
    ai_recommendations = ai_query.scalar() or 0
    common_codes_generated = (
        db.query(func.count(CommonMaterialCode.id)).scalar() or 0
        if not cpse_id
        else common_codes_query.scalar() or 0
    )
    approved_common_codes = approved_codes_query.scalar() or 0

    return DashboardStatistics(
        total_materials=total_materials,
        harmonized_materials=harmonized_materials,
        pending_human_approvals=pending_human_approvals,
        cpses_onboarded=cpses_onboarded,
        duplicate_codes_reduced=_duplicate_codes_reduced(db),
        ai_recommendations=ai_recommendations,
        common_codes_generated=common_codes_generated,
        approved_common_codes=approved_common_codes,
    )


@router.get("/trends", response_model=DashboardTrends)
def get_trends(
    cpse_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_query = db.query(func.count(Material.id))
    harmonized_base = db.query(func.count(Material.id)).filter(Material.status == MaterialStatus.HARMONIZED.value)
    pending_base = db.query(func.count(Material.id)).filter(
        Material.status.in_([MaterialStatus.PENDING.value, MaterialStatus.PROCESSING.value])
    )
    if cpse_id:
        total_query = total_query.filter(Material.cpse_id == cpse_id)
        harmonized_base = harmonized_base.filter(Material.cpse_id == cpse_id)
        pending_base = pending_base.filter(Material.cpse_id == cpse_id)

    total = total_query.scalar() or 0
    harmonized = harmonized_base.scalar() or 0
    pending = pending_base.scalar() or 0
    not_harmonized = max(total - harmonized - pending, 0)
    harmonization_progress = [
        ChartPoint(label="Harmonized", value=harmonized),
        ChartPoint(label="Pending Review", value=pending),
        ChartPoint(label="Not Harmonized", value=not_harmonized),
    ]

    buckets = [
        ("Below 60%", 0, 60),
        ("60-85%", 60, 85),
        ("85-95%", 85, 95),
        ("95-100%", 95, 100.0001),
    ]
    confidence_distribution = []
    for label, low, high in buckets:
        bucket_query = db.query(func.count(AIAnalysis.id)).filter(
            AIAnalysis.final_score >= low, AIAnalysis.final_score < high
        )
        if cpse_id:
            bucket_query = bucket_query.join(Material, AIAnalysis.material_id == Material.id).filter(
                Material.cpse_id == cpse_id
            )
        confidence_distribution.append(ChartPoint(label=label, value=bucket_query.scalar() or 0))

    materials_by_cpse_query = db.query(CPSEOrganization.code, func.count(Material.id)).join(
        Material, Material.cpse_id == CPSEOrganization.id
    )
    if cpse_id:
        materials_by_cpse_query = materials_by_cpse_query.filter(CPSEOrganization.id == cpse_id)
    materials_by_cpse_rows = materials_by_cpse_query.group_by(CPSEOrganization.code).all()
    materials_by_cpse = [ChartPoint(label=code, value=count) for code, count in materials_by_cpse_rows]

    harmonized_by_cpse_query = (
        db.query(CPSEOrganization.code, func.count(Material.id))
        .join(Material, Material.cpse_id == CPSEOrganization.id)
        .filter(Material.status == MaterialStatus.HARMONIZED.value)
    )
    if cpse_id:
        harmonized_by_cpse_query = harmonized_by_cpse_query.filter(CPSEOrganization.id == cpse_id)
    harmonized_by_cpse_rows = harmonized_by_cpse_query.group_by(CPSEOrganization.code).all()
    harmonized_by_cpse = [ChartPoint(label=code, value=count) for code, count in harmonized_by_cpse_rows]

    monthly_query = db.query(
        func.to_char(Material.updated_at, "YYYY-MM").label("month"), func.count(Material.id)
    ).filter(Material.status == MaterialStatus.HARMONIZED.value)
    if cpse_id:
        monthly_query = monthly_query.filter(Material.cpse_id == cpse_id)
    monthly_rows = monthly_query.group_by("month").order_by("month").all()
    monthly_trend = [ChartPoint(label=month, value=count) for month, count in monthly_rows]

    dup_by_category_query = db.query(CommonMaterialCode.category, func.count(Material.id)).join(
        Material, Material.common_code_id == CommonMaterialCode.id
    )
    if cpse_id:
        dup_by_category_query = dup_by_category_query.filter(Material.cpse_id == cpse_id)
    dup_by_category_rows = dup_by_category_query.group_by(CommonMaterialCode.category).all()
    duplicate_reduction = [
        ChartPoint(label=category or "Uncategorized", value=max(count - 1, 0)) for category, count in dup_by_category_rows
    ]

    estimated_savings = [
        ChartPoint(label=point.label, value=round(point.value * ESTIMATED_SAVING_PER_DUPLICATE_INR, 2))
        for point in duplicate_reduction
    ]

    return DashboardTrends(
        harmonization_progress=harmonization_progress,
        confidence_distribution=confidence_distribution,
        materials_by_cpse=materials_by_cpse,
        harmonized_by_cpse=harmonized_by_cpse,
        monthly_trend=monthly_trend,
        duplicate_reduction=duplicate_reduction,
        estimated_savings=estimated_savings,
    )
