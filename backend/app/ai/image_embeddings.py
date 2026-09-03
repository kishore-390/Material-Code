"""
Image embedding generation (CLIP-compatible), with a deterministic
pixel-histogram fallback when the CLIP model / torch cannot be loaded.
Same contract as text_embeddings.py: callers never need to know which
path produced the vector.
"""
import logging
import os

import numpy as np
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_processor = None
_model_load_attempted = False
MOCK_MODEL_NAME = "mock-pixel-histogram-v1"


def _load_model():
    global _model, _processor, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True
    try:
        from transformers import CLIPModel, CLIPProcessor

        _model = CLIPModel.from_pretrained(settings.IMAGE_EMBEDDING_MODEL)
        _processor = CLIPProcessor.from_pretrained(settings.IMAGE_EMBEDDING_MODEL)
        logger.info("Loaded image embedding model %s", settings.IMAGE_EMBEDDING_MODEL)
    except Exception as exc:  # pragma: no cover - depends on environment
        logger.warning("Real image embedding model unavailable (%s)", exc)
        _model = None
    return _model


def _resolve_path(image_url: str) -> str | None:
    if not image_url:
        return None
    relative = image_url.lstrip("/")
    if relative.startswith("uploads/"):
        relative = relative[len("uploads/"):]
    candidate = os.path.join(settings.UPLOAD_DIR, relative)
    return candidate if os.path.exists(candidate) else None


def _mock_embedding(path: str, dim: int) -> list[float]:
    with Image.open(path) as img:
        img = img.convert("RGB").resize((16, 16))
        arr = np.asarray(img, dtype=float).flatten() / 255.0
    if len(arr) >= dim:
        vec = arr[:dim]
    else:
        vec = np.pad(arr, (0, dim - len(arr)))
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def generate_image_embedding(image_url: str | None) -> tuple[list[float] | None, str | None]:
    path = _resolve_path(image_url) if image_url else None
    if not path:
        return None, None

    model = _load_model()
    if model is not None:
        try:
            import torch

            with Image.open(path) as img:
                img = img.convert("RGB")
                inputs = _processor(images=img, return_tensors="pt")
                with torch.no_grad():
                    features = model.get_image_features(**inputs)
                vec = features[0].numpy()
                vec = vec / (np.linalg.norm(vec) or 1.0)
                return vec.tolist(), settings.IMAGE_EMBEDDING_MODEL
        except Exception as exc:  # pragma: no cover
            logger.warning("Image embedding inference failed: %s", exc)
            if not settings.AI_USE_MOCK_FALLBACK:
                raise

    if model is None and not settings.AI_USE_MOCK_FALLBACK:
        raise RuntimeError("Image embedding model unavailable and mock fallback is disabled")

    try:
        return _mock_embedding(path, settings.IMAGE_EMBEDDING_DIM), MOCK_MODEL_NAME
    except Exception as exc:  # pragma: no cover
        logger.warning("Mock image embedding failed for %s: %s", path, exc)
        return None, None
