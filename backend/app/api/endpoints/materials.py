import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.cpse import CPSEOrganization
from app.models.enums import MaterialStatus, NotificationType, RoleName, UploadStatus
from app.models.material import Material, MaterialAttribute, MaterialEmbedding
from app.models.matching import AIAnalysis
from app.models.upload_batch import UploadBatch
from app.models.user import User
from app.schemas.material import (
    BulkImportResponse,
    BulkValidationResponse,
    BulkValidationRow,
    MaterialCreate,
    MaterialDetailOut,
    MaterialListResponse,
    MaterialOut,
    MaterialUpdate,
    SimilarMaterialItem,
)
from app.services import bulk_import, normalization
from app.services.audit_service import log_action
from app.services.file_storage import ALLOWED_IMAGE_EXTENSIONS, save_upload
from app.services.notification_service import notify_role, notify_user

router = APIRouter(prefix="/materials", tags=["Materials"])

_batch_cache: dict[str, dict] = {}


def _material_to_detail(db: Session, material: Material) -> MaterialDetailOut:
    attrs = db.query(MaterialAttribute).filter(MaterialAttribute.material_id == material.id).all()
    has_embedding = (
        db.query(MaterialEmbedding).filter(MaterialEmbedding.material_id == material.id).first() is not None
    )
    out = MaterialDetailOut.model_validate(material)
    out.attributes = attrs
    out.has_embedding = has_embedding
    return out


def _enqueue_ai_analysis(material_id: uuid.UUID) -> None:
    try:
        from app.workers.tasks import ai_analysis

        ai_analysis.delay(str(material_id))
    except Exception:  # noqa: BLE001 - Celery/Redis may be unavailable in constrained dev setups
        pass


# ---- static/collection routes must be declared before /{material_id} ----------------


@router.get("/search", response_model=list[SimilarMaterialItem])
def search_materials(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Intelligent search (spec section 16): blends lexical matches (ILIKE across
    code/description/specification/category/uom) with semantic pgvector
    similarity against the query text's own embedding, so free-text queries
    like "carbon steel seamless pipe" surface ranked matches with a
    similarity percentage even when the wording differs from the source data.
    """
    from app.ai.text_embeddings import generate_text_embedding
    from app.services.scoring import cosine_similarity

    from app.models.harmonization import CommonMaterialCode

    like = f"%{q.strip()}%"
    base_query = db.query(Material)
    if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id:
        base_query = base_query.filter(Material.cpse_id == current_user.cpse_id)

    common_code_ids = db.query(CommonMaterialCode.id).filter(
        or_(CommonMaterialCode.code.ilike(like), CommonMaterialCode.standard_description.ilike(like))
    )

    lexical_matches = base_query.filter(
        or_(
            Material.material_code.ilike(like),
            Material.description.ilike(like),
            Material.specification.ilike(like),
            Material.category.ilike(like),
            Material.uom.ilike(like),
            Material.common_code_id.in_(common_code_ids),
        )
    ).limit(50).all()

    query_vector, _ = generate_text_embedding(normalization.normalize_description(q))
    semantic_matches = (
        base_query.join(MaterialEmbedding, MaterialEmbedding.material_id == Material.id)
        .filter(MaterialEmbedding.text_embedding.isnot(None))
        .order_by(MaterialEmbedding.text_embedding.cosine_distance(query_vector))
        .limit(20)
        .all()
    )

    combined: dict[uuid.UUID, Material] = {m.id: m for m in [*lexical_matches, *semantic_matches]}

    results = []
    for material in combined.values():
        cos = None
        if material.embedding is not None and material.embedding.text_embedding is not None:
            cos = cosine_similarity(query_vector, material.embedding.text_embedding)
        results.append(SimilarMaterialItem(material=material, similarity=round((cos or 0) * 100, 2)))

    results.sort(key=lambda r: r.similarity, reverse=True)
    return results[:30]


def _is_duplicate_error(errors: list[str]) -> bool:
    return any("duplicate" in e.lower() for e in errors)


@router.post("/bulk/validate", response_model=BulkValidationResponse)
def validate_bulk_upload(
    file: UploadFile = File(...),
    cpse_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.CPSE_USER.value)),
):
    default_cpse = None
    if cpse_id is not None:
        default_cpse = db.query(CPSEOrganization).filter(CPSEOrganization.id == cpse_id).first()
        if not default_cpse:
            raise HTTPException(status_code=400, detail="Unknown organization")
        if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id != default_cpse.id:
            raise HTTPException(status_code=403, detail="You may only upload materials for your own CPSE")
        if not default_cpse.is_active:
            raise HTTPException(status_code=400, detail="This organization is inactive")

    try:
        df = bulk_import.read_upload_dataframe(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    results = bulk_import.validate_dataframe(db, df, default_cpse=default_cpse)
    valid_count = sum(1 for r in results if r["is_valid"])
    duplicate_count = sum(1 for r in results if not r["is_valid"] and _is_duplicate_error(r["errors"]))
    invalid_count = len(results) - valid_count - duplicate_count

    upload_batch = None
    if default_cpse is not None:
        upload_batch = UploadBatch(
            cpse_id=default_cpse.id,
            filename=file.filename or "upload",
            uploaded_by=current_user.id,
            total_records=len(results),
            valid_records=valid_count,
            invalid_records=invalid_count,
            duplicate_records=duplicate_count,
            status=UploadStatus.VALIDATING.value,
        )
        db.add(upload_batch)
        db.commit()
        db.refresh(upload_batch)

    batch_token = uuid.uuid4().hex
    _batch_cache[batch_token] = {
        "rows": results,
        "upload_batch_id": upload_batch.id if upload_batch else None,
    }

    return BulkValidationResponse(
        batch_token=batch_token,
        upload_batch_id=upload_batch.id if upload_batch else None,
        total_rows=len(results),
        valid_rows=valid_count,
        invalid_rows=invalid_count + duplicate_count,
        rows=[BulkValidationRow(**r) for r in results],
    )


@router.post("/bulk/import", response_model=BulkImportResponse)
def import_bulk_upload(
    batch_token: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.CPSE_USER.value)),
):
    cached = _batch_cache.get(batch_token)
    if cached is None:
        raise HTTPException(status_code=404, detail="Validation batch not found or expired. Please re-validate.")

    rows = cached["rows"]
    valid_rows = [r for r in rows if r["is_valid"]]
    upload_batch_id = cached.get("upload_batch_id")

    if upload_batch_id is None:
        # Legacy path: no organization was pre-selected at validate time (a mixed-CPSE
        # file with a per-row "cpse" column), so there's no single org to attribute a
        # history record to. Fall back to importing synchronously, same as before.
        created_ids = bulk_import.import_valid_rows(db, valid_rows, current_user.id)
        for material_id in created_ids:
            _enqueue_ai_analysis(material_id)
        log_action(
            db,
            action="BULK_UPLOAD_COMPLETED",
            entity_type="material",
            entity_id=None,
            actor_id=current_user.id,
            actor_name=current_user.full_name,
            actor_type="USER",
            details={"total_uploaded": len(rows), "imported": len(created_ids)},
        )
        _batch_cache.pop(batch_token, None)
        return BulkImportResponse(
            upload_batch_id=uuid.uuid4(),
            status=UploadStatus.COMPLETED.value,
            total_uploaded=len(rows),
            validation_errors=len(rows) - len(valid_rows),
        )

    batch = db.query(UploadBatch).filter(UploadBatch.id == upload_batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Upload batch not found")

    if not valid_rows:
        batch.status = UploadStatus.COMPLETED.value
        db.commit()
    else:
        batch.status = UploadStatus.QUEUED.value
        db.commit()
        try:
            from app.workers.tasks import process_bulk_import

            process_bulk_import.delay(str(batch.id), valid_rows, str(current_user.id))
        except Exception:  # noqa: BLE001 - Celery/Redis may be unavailable in constrained dev setups
            pass

    log_action(
        db,
        action="BULK_UPLOAD_QUEUED",
        entity_type="material",
        entity_id=None,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"total_uploaded": len(rows), "queued": len(valid_rows), "cpse": batch.cpse.code},
    )
    notify_user(
        db,
        current_user.id,
        NotificationType.BULK_UPLOAD_COMPLETED.value,
        "Bulk upload queued",
        f"{len(valid_rows)} of {len(rows)} rows for {batch.cpse.code} were queued for import and AI processing.",
    )
    _batch_cache.pop(batch_token, None)

    return BulkImportResponse(
        upload_batch_id=batch.id,
        status=batch.status,
        total_uploaded=len(rows),
        validation_errors=len(rows) - len(valid_rows),
    )


@router.get("/bulk/status")
def bulk_status(
    ids: str = Query(..., description="Comma-separated material UUIDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    id_list = [uuid.UUID(i) for i in ids.split(",") if i.strip()]
    materials = db.query(Material.status).filter(Material.id.in_(id_list)).all()
    counts: dict[str, int] = {}
    for (status_value,) in materials:
        counts[status_value] = counts.get(status_value, 0) + 1
    return {"total": len(id_list), "counts": counts}


# ---- collection ----------------------------------------------------------------------


@router.post("", response_model=MaterialDetailOut, status_code=status.HTTP_201_CREATED)
def create_material(
    material_code: str = Form(...),
    description: str = Form(...),
    specification: str | None = Form(None),
    category: str = Form(...),
    uom: str = Form(...),
    cpse_code: str = Form(...),
    manufacturer: str | None = Form(None),
    brand: str | None = Form(None),
    material_type: str | None = Form(None),
    attributes_json: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.CPSE_USER.value)),
):
    cpse = db.query(CPSEOrganization).filter(CPSEOrganization.code == cpse_code.upper()).first()
    if not cpse:
        raise HTTPException(status_code=400, detail=f"Unknown CPSE '{cpse_code}'")

    if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id != cpse.id:
        raise HTTPException(status_code=403, detail="You may only upload materials for your own CPSE")

    existing = (
        db.query(Material)
        .filter(Material.material_code == material_code, Material.cpse_id == cpse.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate material code for this CPSE")

    attributes: dict[str, str] = {}
    if attributes_json:
        try:
            attributes = json.loads(attributes_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="attributes_json must be valid JSON") from exc

    image_url = None
    if image is not None and image.filename:
        try:
            image_url = save_upload(image, "materials", ALLOWED_IMAGE_EXTENSIONS)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    material = Material(
        material_code=material_code,
        description=description,
        normalized_description=normalization.normalize_description(description),
        specification=specification,
        normalized_specification=normalization.normalize_specification(specification),
        category=category,
        normalized_category=normalization.normalize_category(category),
        uom=uom,
        normalized_uom=normalization.normalize_uom(uom),
        cpse_id=cpse.id,
        manufacturer=manufacturer,
        brand=brand,
        material_type=material_type,
        status=MaterialStatus.PENDING.value,
        image_url=image_url,
        created_by=current_user.id,
    )
    db.add(material)
    db.flush()

    for key, value in attributes.items():
        db.add(MaterialAttribute(material_id=material.id, attr_key=key, attr_value=str(value)))

    db.commit()
    db.refresh(material)

    log_action(
        db,
        action="MATERIAL_UPLOADED",
        entity_type="material",
        entity_id=material.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details={"material_code": material.material_code, "cpse": cpse.code},
    )
    notify_role(
        db,
        RoleName.ADMIN.value,
        NotificationType.MATERIAL_UPLOADED.value,
        "New material uploaded",
        f"{material.material_code} was uploaded by {current_user.full_name} ({cpse.code}).",
        "material",
        material.id,
    )
    _enqueue_ai_analysis(material.id)

    return _material_to_detail(db, material)


@router.get("", response_model=MaterialListResponse)
def list_materials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cpse_id: uuid.UUID | None = None,
    category: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    common_code: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    query = db.query(Material)

    if current_user.role.name == RoleName.CPSE_USER.value and current_user.cpse_id:
        query = query.filter(Material.cpse_id == current_user.cpse_id)
    elif cpse_id:
        query = query.filter(Material.cpse_id == cpse_id)

    if category:
        query = query.filter(Material.category.ilike(f"%{category}%"))
    if status_filter:
        query = query.filter(Material.status == status_filter)
    if common_code:
        query = query.join(Material.common_code).filter_by(code=common_code)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Material.material_code.ilike(like), Material.description.ilike(like))
        )

    total = query.count()
    items = (
        query.order_by(Material.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return MaterialListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{material_id}", response_model=MaterialDetailOut)
def get_material(material_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return _material_to_detail(db, material)


@router.put("/{material_id}", response_model=MaterialDetailOut)
def update_material(
    material_id: uuid.UUID,
    payload: MaterialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value, RoleName.CPSE_USER.value)),
):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if current_user.role.name == RoleName.CPSE_USER.value and material.cpse_id != current_user.cpse_id:
        raise HTTPException(status_code=403, detail="You may only edit your own CPSE's materials")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(material, field, value)
    if "description" in data:
        material.normalized_description = normalization.normalize_description(material.description)
    if "specification" in data:
        material.normalized_specification = normalization.normalize_specification(material.specification)
    if "category" in data:
        material.normalized_category = normalization.normalize_category(material.category)
    if "uom" in data:
        material.normalized_uom = normalization.normalize_uom(material.uom)

    db.commit()
    db.refresh(material)
    log_action(
        db,
        action="MATERIAL_UPDATED",
        entity_type="material",
        entity_id=material.id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
        details=data,
    )
    return _material_to_detail(db, material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.ADMIN.value)),
):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    db.delete(material)
    db.commit()
    log_action(
        db,
        action="MATERIAL_DELETED",
        entity_type="material",
        entity_id=material_id,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        actor_type="USER",
    )


@router.get("/{material_id}/similar", response_model=list[SimilarMaterialItem])
def similar_materials(
    material_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.ai.similarity import find_candidate_materials

    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if not material.embedding:
        return []

    from app.services.scoring import cosine_similarity

    candidates = find_candidate_materials(db, material, limit=limit)
    results = []
    for cand in candidates:
        cos = cosine_similarity(
            material.embedding.text_embedding, cand.embedding.text_embedding if cand.embedding else None
        )
        results.append(SimilarMaterialItem(material=cand, similarity=round((cos or 0) * 100, 2)))
    results.sort(key=lambda r: r.similarity, reverse=True)
    return results
