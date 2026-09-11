"""
Procurement intelligence (spec section 15). Reads only real
procurement_history rows (demo rows are explicitly flagged is_demo_data and
that flag is always surfaced, never hidden) grouped by common material, so
"potential collaborative procurement" is a real aggregation of whatever
history rows currently exist - never an invented savings figure.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.enums import MappingDecisionStatus
from app.models.harmonization import CommonMaterial, CommonMaterialMapping
from app.models.material import CPSEMaterial
from app.models.procurement import ProcurementHistory

_NON_REJECTED = CommonMaterialMapping.decision_status != MappingDecisionStatus.REJECTED.value


@dataclass
class CPSEDemand:
    cpse_code: str
    cpse_name: str
    total_quantity: float
    uom: str | None


@dataclass
class CollaborativeOpportunity:
    common_code: str
    standardized_description: str
    cpse_demand: list[CPSEDemand]
    total_potential_aggregated_demand: float
    uom: str | None
    includes_demo_data: bool


def list_collaborative_opportunities(db: Session, *, limit: int = 20) -> list[CollaborativeOpportunity]:
    common_materials = (
        db.query(CommonMaterial)
        .join(CommonMaterialMapping, CommonMaterialMapping.common_material_id == CommonMaterial.id)
        .filter(_NON_REJECTED)
        .group_by(CommonMaterial.id)
        .having(func.count(func.distinct(CommonMaterialMapping.cpse_material_id)) > 1)
        .all()
    )

    opportunities: list[CollaborativeOpportunity] = []
    for common_material in common_materials:
        mappings = (
            db.query(CommonMaterialMapping)
            .options(joinedload(CommonMaterialMapping.cpse_material).joinedload(CPSEMaterial.cpse))
            .filter(CommonMaterialMapping.common_material_id == common_material.id, _NON_REJECTED)
            .all()
        )
        member_ids = [m.cpse_material_id for m in mappings]
        records = db.query(ProcurementHistory).filter(ProcurementHistory.cpse_material_id.in_(member_ids)).all()
        if not records:
            continue

        by_cpse: dict[uuid.UUID, list[ProcurementHistory]] = {}
        for r in records:
            material = next((m.cpse_material for m in mappings if m.cpse_material_id == r.cpse_material_id), None)
            if material is None:
                continue
            by_cpse.setdefault(material.cpse_id, []).append(r)

        cpse_demand: list[CPSEDemand] = []
        total = 0.0
        includes_demo = False
        for cpse_id, cpse_records in by_cpse.items():
            material = next(m.cpse_material for m in mappings if m.cpse_material_id == cpse_records[0].cpse_material_id)
            qty = sum(r.quantity for r in cpse_records)
            total += qty
            includes_demo = includes_demo or any(r.is_demo_data for r in cpse_records)
            cpse_demand.append(
                CPSEDemand(cpse_code=material.cpse.code, cpse_name=material.cpse.name, total_quantity=qty, uom=cpse_records[0].uom)
            )

        opportunities.append(
            CollaborativeOpportunity(
                common_code=common_material.common_code,
                standardized_description=common_material.standardized_description,
                cpse_demand=sorted(cpse_demand, key=lambda d: d.total_quantity, reverse=True),
                total_potential_aggregated_demand=total,
                uom=common_material.standardized_uom,
                includes_demo_data=includes_demo,
            )
        )

    opportunities.sort(key=lambda o: o.total_potential_aggregated_demand, reverse=True)
    return opportunities[:limit]


def estimate_total_aggregation_value(db: Session) -> float:
    """Sum of potential aggregated demand across every opportunity - a
    quantity-based estimate, never a monetary savings claim (spec section 15)."""
    return round(sum(o.total_potential_aggregated_demand for o in list_collaborative_opportunities(db, limit=1000)), 2)
