import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import MappingDecisionStatus
from app.models.material import CPSEMaterial, MaterialAttribute, MaterialEmbedding
from app.models.user import User
from app.schemas.material import CPSEMaterialDetailOut, CPSEMaterialOut, MaterialListResponse
from app.services import normalization

router = APIRouter(prefix="/cpse-materials", tags=["CPSE Materials"])


def _material_to_detail(db: Session, material: CPSEMaterial) -> CPSEMaterialDetailOut:
    attrs = db.query(MaterialAttribute).filter(MaterialAttribute.material_id == material.id).all()
    has_embedding = (
        db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == material.id).first() is not None
    )
    active = next((m for m in material.mappings if m.decision_status != MappingDecisionStatus.REJECTED.value), None)

    out = CPSEMaterialDetailOut.model_validate(material)
    out.attributes = attrs
    out.has_embedding = has_embedding
    out.active_common_material = active.common_material if active else None
    return out


@router.get("/search", response_model=list[CPSEMaterialOut])
def search_materials(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Intelligent search (spec section 16): blends lexical matches (ILIKE
    across code/description/specification/classification/uom) with semantic
    pgvector similarity against the query text's own embedding.
    """
    from app.ai.text_embeddings import generate_text_embedding

    like = f"%{q.strip()}%"
    lexical_matches = (
        db.query(CPSEMaterial)
        .filter(
            or_(
                CPSEMaterial.original_material_code.ilike(like),
                CPSEMaterial.original_description.ilike(like),
                CPSEMaterial.technical_specification.ilike(like),
                CPSEMaterial.classification.ilike(like),
                CPSEMaterial.uom.ilike(like),
            )
        )
        .limit(50)
        .all()
    )

    query_vector, _ = generate_text_embedding(normalization.normalize_description(q))
    semantic_matches = (
        db.query(CPSEMaterial)
        .join(MaterialEmbedding, MaterialEmbedding.material_id == CPSEMaterial.id)
        .filter(MaterialEmbedding.text_embedding.isnot(None))
        .order_by(MaterialEmbedding.text_embedding.cosine_distance(query_vector))
        .limit(20)
        .all()
    )

    combined: dict[uuid.UUID, CPSEMaterial] = {m.id: m for m in [*lexical_matches, *semantic_matches]}
    return list(combined.values())[:30]


@router.get("", response_model=MaterialListResponse)
def list_materials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cpse_id: uuid.UUID | None = None,
    classification: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    mapped_only: bool | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    query = db.query(CPSEMaterial)

    if cpse_id:
        query = query.filter(CPSEMaterial.cpse_id == cpse_id)
    if classification:
        query = query.filter(CPSEMaterial.classification.ilike(f"%{classification}%"))
    if status_filter:
        query = query.filter(CPSEMaterial.status == status_filter)
    if mapped_only is not None:
        query = query.filter(CPSEMaterial.mappings.any() if mapped_only else ~CPSEMaterial.mappings.any())
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(CPSEMaterial.original_material_code.ilike(like), CPSEMaterial.original_description.ilike(like))
        )

    total = query.count()
    items = (
        query.order_by(CPSEMaterial.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MaterialListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{material_id}", response_model=CPSEMaterialDetailOut)
def get_material(material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    material = db.query(CPSEMaterial).filter(CPSEMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="CPSE material not found")
    return _material_to_detail(db, material)


@router.get("/{material_id}/similar", response_model=list[CPSEMaterialOut])
def similar_materials(
    material_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.ai.similarity import find_candidate_materials

    material = db.query(CPSEMaterial).filter(CPSEMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="CPSE material not found")
    if not material.embedding:
        return []
    return find_candidate_materials(db, material, limit=limit)
