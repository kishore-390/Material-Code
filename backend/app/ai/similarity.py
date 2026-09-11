"""
pgvector-backed candidate retrieval (spec section 7).

We deliberately never compare a new material against the whole table.
Instead we combine an ANN vector search (cosine distance on the text
embedding, indexed via pgvector) with a metadata filter on normalized
classification so the search space collapses to a handful of plausible
candidates before the more expensive detailed scoring pass runs.
"""
from sqlalchemy.orm import Session

from app.models.material import CPSEMaterial, MaterialEmbedding
from app.models.enums import MaterialStatus

DEFAULT_CANDIDATE_LIMIT = 5


def find_candidate_materials(
    db: Session, material: CPSEMaterial, limit: int = DEFAULT_CANDIDATE_LIMIT
) -> list[CPSEMaterial]:
    if material.embedding is None or material.embedding.text_embedding is None:
        return []

    query_vector = material.embedding.text_embedding

    base_query = (
        db.query(CPSEMaterial)
        .join(MaterialEmbedding, MaterialEmbedding.material_id == CPSEMaterial.id)
        .filter(CPSEMaterial.id != material.id)
        .filter(CPSEMaterial.status != MaterialStatus.FAILED.value)
        .filter(MaterialEmbedding.text_embedding.isnot(None))
    )

    candidates: list[CPSEMaterial] = []
    if material.normalized_classification:
        candidates = (
            base_query.filter(CPSEMaterial.normalized_classification == material.normalized_classification)
            .order_by(MaterialEmbedding.text_embedding.cosine_distance(query_vector))
            .limit(limit)
            .all()
        )

    if not candidates:
        # metadata filter found nothing (e.g. a brand-new classification) - widen the search
        candidates = (
            base_query.order_by(MaterialEmbedding.text_embedding.cosine_distance(query_vector))
            .limit(limit)
            .all()
        )

    return candidates
