"""
Local filesystem storage for uploaded files (spec section 25).

Kept behind a tiny interface so a future S3/MinIO backend can be dropped
in without touching callers: everything here only deals in
(sub_directory, filename) -> public URL path.
"""
import os
import uuid

from fastapi import UploadFile
from slugify import slugify

from app.core.config import settings

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_DOCUMENT_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def _safe_filename(original_name: str) -> str:
    name, ext = os.path.splitext(original_name or "file")
    ext = ext.lower()
    safe_name = slugify(name)[:80] or "file"
    return f"{safe_name}-{uuid.uuid4().hex[:8]}{ext}"


def save_upload(file: UploadFile, sub_dir: str, allowed_extensions: set[str] | None = None) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if allowed_extensions and ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type '{ext}'. Allowed: {sorted(allowed_extensions)}")

    target_dir = os.path.join(settings.UPLOAD_DIR, sub_dir)
    os.makedirs(target_dir, exist_ok=True)

    filename = _safe_filename(file.filename or "upload")
    full_path = os.path.join(target_dir, filename)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    contents = file.file.read()
    if len(contents) > max_bytes:
        raise ValueError(f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB} MB")

    with open(full_path, "wb") as f:
        f.write(contents)

    return f"/uploads/{sub_dir}/{filename}"
