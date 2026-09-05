"""
Deterministic technical-conflict detector.

Semantic similarity (SBERT/pgvector/XGBoost) can score two descriptions as
"almost the same wording" even when they name incompatible engineering
specifications - e.g. "SS BOLT M10" vs "SS BOLT M12" read as nearly
identical text but are not interchangeable parts. This module extracts
real numeric/grade tokens that are already present in the material's own
description + specification text (reusing the same cleaning
normalization.basic_clean already applies everywhere else) and flags a
conflict only when both materials mention a token in the *same* technical
category (material grade, dimension, thread/bolt size, voltage, pressure)
and none of the values on either side match.

This never fabricates a conflict: if only one side mentions a dimension,
or the same value appears on both sides, nothing is flagged. It is a
second, independent signal alongside the existing similarity score - not
a replacement for it.
"""
import re
from dataclasses import dataclass

from app.services.normalization import basic_clean

_GRADE_RE = re.compile(r"\b(SS|MS|CS|GI|CI|IS|EN|AISI|ASTM|A)\s?-?(\d{3,4})\b")
_VOLTAGE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?-?(KV|V)\b")
_PRESSURE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?-?(BAR|PSI|MPA)\b")
_THREAD_RE = re.compile(r"\bM(\d+(?:\.\d+)?)\b")
_DIMENSION_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?-?(MM|CM)\b")

_PATTERNS: list[tuple[str, "re.Pattern[str]", "callable"]] = [
    ("Material grade", _GRADE_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Voltage rating", _VOLTAGE_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Pressure rating", _PRESSURE_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Thread/bolt size", _THREAD_RE, lambda m: f"M{m.group(1)}"),
    ("Dimension", _DIMENSION_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
]


@dataclass
class ConflictResult:
    has_conflict: bool
    reasons: list[str]


def _extract(text: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for label, pattern, normalize in _PATTERNS:
        matches = {normalize(m) for m in pattern.finditer(text)}
        if matches:
            found[label] = matches
    return found


def detect_conflict(text_a: str, text_b: str) -> ConflictResult:
    """Compares two materials' combined description+specification text for
    genuine technical incompatibilities - distinct from semantic
    dissimilarity, which the existing scoring pipeline already handles."""
    tokens_a = _extract(basic_clean(text_a))
    tokens_b = _extract(basic_clean(text_b))

    reasons: list[str] = []
    for label in sorted(tokens_a.keys() & tokens_b.keys()):
        if tokens_a[label].isdisjoint(tokens_b[label]):
            reasons.append(
                f"{label} mismatch: {', '.join(sorted(tokens_a[label]))} vs {', '.join(sorted(tokens_b[label]))}"
            )
    return ConflictResult(has_conflict=bool(reasons), reasons=reasons)
