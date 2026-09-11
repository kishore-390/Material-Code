"""
Shared regex vocabulary for pulling structured technical tokens out of free
text (spec section 7.2 - attribute extraction). Used by both
app.ai.conflict_detector (does two materials disagree on a token in the
same category?) and app.services.attribute_extraction (backfilling
material_grade/dimensions/standard when a CPSE's source table doesn't carry
them as separate columns) - one regex vocabulary, never duplicated.
"""
import re

GRADE_RE = re.compile(r"\b(SS|MS|CS|GI|CI|IS|EN|AISI|ASTM|A)\s?-?(\d{3,4})\b")
VOLTAGE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?-?(KV|V)\b")
PRESSURE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?-?(BAR|PSI|MPA)\b")
THREAD_RE = re.compile(r"\bM(\d+(?:\.\d+)?)\b")
DIMENSION_MM_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?-?(MM|CM)\b")
DIMENSION_INCH_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:"|INCH|INCHES|IN)\b')
STANDARD_RE = re.compile(r"\b(ASTM|ANSI|API|BS|DIN|IS|ISO)\s?-?([A-Z]?\d{1,4}[A-Z]?)\b")

# label -> (pattern, normalizer). Shared by conflict detection (same-category
# token disagreement) and attribute extraction (first match wins).
TECHNICAL_TOKEN_PATTERNS: list[tuple[str, "re.Pattern[str]", "callable"]] = [
    ("Material grade", GRADE_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Voltage rating", VOLTAGE_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Pressure rating", PRESSURE_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Thread/bolt size", THREAD_RE, lambda m: f"M{m.group(1)}"),
    ("Dimension", DIMENSION_MM_RE, lambda m: f"{m.group(1)}{m.group(2)}"),
    ("Dimension (inch)", DIMENSION_INCH_RE, lambda m: f'{m.group(1)}IN'),
]
