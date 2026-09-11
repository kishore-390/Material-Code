"""
Attribute extraction (spec section 7.2) - backfills material_grade,
dimensions and standard from a CPSE material's free-text description/
specification when its source table didn't supply them as separate
columns. Reuses the exact regex vocabulary app.ai.conflict_detector uses
to extract the same categories, so extraction and conflict detection can
never disagree about what a "grade" or "dimension" token looks like.

Never overwrites a value the CPSE's own source explicitly provided -
extraction only fills gaps, it never second-guesses source data.
"""
from app.ai.attribute_patterns import GRADE_RE, STANDARD_RE, THREAD_RE, DIMENSION_MM_RE, DIMENSION_INCH_RE
from app.services.normalization import basic_clean


def _first_match(pattern, text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def extract_missing_attributes(
    *,
    description: str,
    specification: str | None,
    material_grade: str | None,
    dimensions: str | None,
    standard: str | None,
) -> dict[str, str | None]:
    """Returns {field: value} only for fields that were empty and a token
    was found - callers merge this into the record, never blindly overwrite."""
    text = basic_clean(f"{description} {specification or ''}")
    result: dict[str, str | None] = {}

    if not material_grade:
        result["material_grade"] = _first_match(GRADE_RE, text)
    if not dimensions:
        result["dimensions"] = _first_match(THREAD_RE, text) or _first_match(DIMENSION_MM_RE, text) or _first_match(
            DIMENSION_INCH_RE, text
        )
    if not standard:
        result["standard"] = _first_match(STANDARD_RE, text)

    return {k: v for k, v in result.items() if v}
