import itertools

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.duplicate_code import (
    DuplicateCodeCompareOut,
    DuplicateCodeGroupOut,
    DuplicateCodeListResponse,
    DuplicateCodeMaterialOut,
    DuplicateCodePairOut,
)
from app.services import duplicate_code_service

router = APIRouter(prefix="/legacy-codes", tags=["Legacy Material Codes"])


@router.get("", response_model=DuplicateCodeListResponse)
def list_duplicate_codes(
    q: str | None = Query(None, description="Search by original material code"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Every original_material_code string supplied by two or more different
    CPSEs - a separate concept from AI-detected material equivalence (see
    /api/harmonization/* for that). See app.services.duplicate_code_service
    for the read-only grouping query.
    """
    groups = duplicate_code_service.list_duplicate_code_groups(db, q=q)
    summary = duplicate_code_service.count_duplicate_codes_summary(db)

    total = len(groups)
    start = (page - 1) * page_size
    page_groups = groups[start : start + page_size]

    items = [
        DuplicateCodeGroupOut(
            original_material_code=g.original_material_code,
            cpses=sorted({m.cpse.code for m in g.materials}),
            materials_count=len(g.materials),
        )
        for g in page_groups
    ]

    return DuplicateCodeListResponse(
        items=items,
        total=total,
        total_duplicate_codes=summary["total_duplicate_codes"],
        cpses_affected=summary["cpses_affected"],
        materials_affected=summary["materials_affected"],
    )


@router.get("/{original_material_code}", response_model=DuplicateCodeCompareOut)
def compare_duplicate_code(
    original_material_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    group = duplicate_code_service.get_duplicate_code_group(db, original_material_code)
    if group is None:
        raise HTTPException(status_code=404, detail="No duplicate source code group found for this material code")

    materials_out = [DuplicateCodeMaterialOut.model_validate(m) for m in group.materials]
    pairs = [
        DuplicateCodePairOut(
            material_a_id=a.id,
            material_b_id=b.id,
            classification=duplicate_code_service.classify_pair(a, b),
        )
        for a, b in itertools.combinations(group.materials, 2)
    ]

    return DuplicateCodeCompareOut(
        original_material_code=group.original_material_code, materials=materials_out, pairs=pairs
    )
