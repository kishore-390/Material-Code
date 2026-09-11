import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.material import CPSEMaterial
from app.models.matching import AIAnalysis, MaterialMatch
from app.models.user import User
from app.schemas.ai import AIAnalysisOut, AnalyzeTriggerResponse, CandidateOut

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@router.post("/analyze/{material_id}", response_model=AnalyzeTriggerResponse)
def trigger_analysis(material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    material = db.query(CPSEMaterial).filter(CPSEMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="CPSE material not found")

    from app.workers.tasks import ai_analysis

    task_id = None
    try:
        result = ai_analysis.delay(str(material_id))
        task_id = result.id
    except Exception:  # noqa: BLE001
        # No broker reachable (e.g. isolated unit test) - run inline so the demo still works.
        from app.ai.analyzer import analyze_material

        analyze_material(db, material_id)

    return AnalyzeTriggerResponse(material_id=material_id, task_id=task_id, status="QUEUED")


@router.get("/analysis/{material_id}", response_model=AIAnalysisOut)
def get_analysis(material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    analysis = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.material_id == material_id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No AI analysis found for this material yet")
    return analysis


@router.get("/analysis/{material_id}/candidates", response_model=list[CandidateOut])
def get_candidates(material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    matches = (
        db.query(MaterialMatch)
        .filter(MaterialMatch.material_id == material_id)
        .order_by(MaterialMatch.final_score.desc())
        .limit(5)
        .all()
    )
    return [
        CandidateOut(
            material=m.candidate,
            final_score=m.final_score,
            description_score=m.description_score,
            specification_score=m.specification_score,
            classification_score=m.classification_score,
            uom_score=m.uom_score,
            attribute_score=m.attribute_score,
            grade_score=m.grade_score,
            dimension_score=m.dimension_score,
            standard_score=m.standard_score,
            manufacturer_score=m.manufacturer_score,
            function_score=m.function_score,
            criticality_score=m.criticality_score,
        )
        for m in matches
    ]
