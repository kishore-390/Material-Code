import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.material import Material
from app.models.matching import AIAnalysis, MaterialMatch
from app.models.user import User
from app.schemas.ai import AIAnalysisOut, AnalyzeTriggerResponse, CandidateOut

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@router.post("/analyze/{material_id}", response_model=AnalyzeTriggerResponse)
def trigger_analysis(material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

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

    matches = (
        db.query(MaterialMatch)
        .filter(MaterialMatch.material_id == material_id)
        .order_by(MaterialMatch.final_score.desc())
        .limit(5)
        .all()
    )
    candidates = [
        CandidateOut(
            material=m.candidate,
            final_score=m.final_score,
            description_score=m.description_score,
            specification_score=m.specification_score,
            category_score=m.category_score,
            uom_score=m.uom_score,
            image_score=m.image_score,
            attribute_score=m.attribute_score,
        )
        for m in matches
    ]

    out = AIAnalysisOut.model_validate(analysis)
    out.candidates = candidates
    return out
