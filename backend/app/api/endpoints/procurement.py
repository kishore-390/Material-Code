import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.procurement import ProcurementHistory
from app.models.user import User
from app.schemas.procurement import CollaborativeProcurementOpportunity, CPSEDemand, ProcurementRecordOut
from app.services import procurement_service

router = APIRouter(prefix="/procurement", tags=["Procurement"])


@router.get("/history/{cpse_material_id}", response_model=list[ProcurementRecordOut])
def get_history(cpse_material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(ProcurementHistory)
        .filter(ProcurementHistory.cpse_material_id == cpse_material_id)
        .order_by(ProcurementHistory.purchase_date.desc())
        .all()
    )


@router.get("/opportunities", response_model=list[CollaborativeProcurementOpportunity])
def list_opportunities(limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    opportunities = procurement_service.list_collaborative_opportunities(db, limit=limit)
    return [
        CollaborativeProcurementOpportunity(
            common_code=o.common_code,
            standardized_description=o.standardized_description,
            cpse_demand=[CPSEDemand(cpse_code=d.cpse_code, cpse_name=d.cpse_name, total_quantity=d.total_quantity, uom=d.uom) for d in o.cpse_demand],
            total_potential_aggregated_demand=o.total_potential_aggregated_demand,
            uom=o.uom,
            includes_demo_data=o.includes_demo_data,
        )
        for o in opportunities
    ]
