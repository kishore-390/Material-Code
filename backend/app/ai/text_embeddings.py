"""
Text embedding generation.

Tries to load a real sentence-transformers model on first use. If the
model cannot be loaded (no internet access in an offline demo
environment, model not cached, etc.) it transparently falls back to a
deterministic hashing-based bag-of-words embedding of the same
dimensionality, so every downstream consumer (pgvector column, cosine
similarity, scoring) works identically either way. Swapping in a real
model later requires no API changes -- see `generate_text_embedding`.

AI_USE_MOCK_FALLBACK controls whether the mock is *allowed* when the
real model can't be loaded. If it is False and the real model fails to
load, the caller sees the exception instead of silently degrading.
"""
import hashlib
import logging

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_load_attempted = False
MOCK_MODEL_NAME = "mock-hashing-bow-v1"


def _load_model():
    global _model, _model_load_attempted
    if _model_load_attempted:
        return _model
    _model_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.TEXT_EMBEDDING_MODEL)
        logger.info("Loaded text embedding model %s", settings.TEXT_EMBEDDING_MODEL)
    except Exception as exc:  # pragma: no cover - depends on environment
        logger.warning("Real text embedding model unavailable (%s)", exc)
        _model = None
    return _model


def _mock_embedding(text: str, dim: int) -> list[float]:
    vec = np.zeros(dim, dtype=float)
    tokens = [t for t in text.upper().split() if t]
    if not tokens:
        return vec.tolist()
    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        h = int(digest, 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign
        idx2 = (h // 7) % dim
        vec[idx2] += sign * 0.5
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def generate_text_embedding(text: str | None) -> tuple[list[float], str]:
    """Returns (embedding_vector, model_name_used)."""
    text = (text or "").strip()
    model = _load_model()
    if model is not None and text:
        try:
            embedding = model.encode(text, normalize_embeddings=True)
            return list(map(float, embedding)), settings.TEXT_EMBEDDING_MODEL
        except Exception as exc:  # pragma: no cover
            logger.warning("Text embedding inference failed: %s", exc)
            if not settings.AI_USE_MOCK_FALLBACK:
                raise

    if model is None and not settings.AI_USE_MOCK_FALLBACK:
        raise RuntimeError("Text embedding model unavailable and mock fallback is disabled")

    return _mock_embedding(text, settings.EMBEDDING_DIM), MOCK_MODEL_NAME
