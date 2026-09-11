from typing import Optional

from pydantic import BaseModel

from app.schemas.harmonization import CommonMaterialOut
from app.schemas.material import CPSEMaterialOut


class DuplicatePairOut(BaseModel):
    mapping_id: str
    common_material: CommonMaterialOut
    source_material: CPSEMaterialOut
    matched_material: CPSEMaterialOut
    mapping_type: str
    decision_status: str
    confidence_score: Optional[float] = None


class DuplicateListResponse(BaseModel):
    items: list[DuplicatePairOut]
    total: int
    page: int
    page_size: int
    # Summary cards - always computed from the FULL, unfiltered set for this
    # user's scope, so they stay stable while the table below is
    # searched/filtered, and use the exact same grouping as the Dashboard's
    # KPI (see app.services.duplicate_service), so the numbers never drift apart.
    total_duplicates: int
    pending_validation: int
    approved: int
    common_materials_generated: int


class DuplicatePairDetailOut(BaseModel):
    mapping_id: str
    common_material: CommonMaterialOut
    source_material: CPSEMaterialOut
    matched_material: CPSEMaterialOut
    mapping_type: str
    decision_status: str
    confidence_score: Optional[float] = None
    breakdown: Optional[dict] = None
    sbert_similarity: Optional[float] = None
    ml_probability: Optional[float] = None
    ml_status: Optional[str] = None
