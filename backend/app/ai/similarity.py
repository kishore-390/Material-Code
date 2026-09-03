"""
pgvector-backed candidate retrieval (spec section 7).

We deliberately never compare a new material against the whole table.
Instead we combine an ANN vector search (cosine distance on the text
embedding, indexed via pgvector) with a metadata filter on normalized
category so the search space collapses to a handful of plausible
candidates before the more expensive detailed scoring pass runs.
"""
from sqlalchemy.orm import Session

from app.models.material import Material, MaterialEmbedding
from app.models.enums import MaterialStatus

DEFAULT_CANDIDATE_LIMIT = 5


def find_candidate_materials(db: Session, material: Material, limit: int = DEFAULT_CANDIDATE_LIMIT) -> list[Material]:
    if material.embedding is None or material.embedding.text_embedding is None:
        return []

    query_vector = material.embedding.text_embedding

    base_query = (
        db.query(Material)
        .join(MaterialEmbedding, MaterialEmbedding.material_id == Material.id)
        .filter(Material.id != material.id)
        .filter(Material.status != MaterialStatus.FAILED.value)
        .filter(MaterialEmbedding.text_embedding.isnot(None))
    )

    candidates: list[Material] = []
    if material.normalized_category:
        candidates = (
            base_query.filter(Material.normalized_category == material.normalized_category)
            .order_by(MaterialEmbedding.text_embedding.cosine_distance(query_vector))
            .limit(limit)
            .all()
        )

    if not candidates:
        # metadata filter found nothing (e.g. a brand-new category) - widen the search
        candidates = (
            base_query.order_by(MaterialEmbedding.text_embedding.cosine_distance(query_vector))
            .limit(limit)
            .all()
        )

    return candidates
