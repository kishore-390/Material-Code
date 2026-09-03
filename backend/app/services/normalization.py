"""
Data normalization for material master fields.

The AI comparison stage never sees raw free-text directly -- it compares
*normalized* representations while the *original* values are always
preserved in the database (see Material.description vs
Material.normalized_description, etc.). This module implements the rules
described in section 6 of the platform spec: normalize capitalization,
whitespace, punctuation, unit/abbreviation vocabulary and dimensional
formats, without discarding or overwriting the source data.
"""
import re

# --- Unit of Measure vocabulary -------------------------------------------------
UOM_MAP: dict[str, str] = {
    "M": "METER", "MT": "METER", "MTR": "METER", "MTRS": "METER",
    "METER": "METER", "METERS": "METER", "METRE": "METER", "METRES": "METER",
    "KG": "KILOGRAM", "KGS": "KILOGRAM", "KILOGRAM": "KILOGRAM", "KILOGRAMS": "KILOGRAM",
    "NOS": "NUMBERS", "NO": "NUMBERS", "NUMBER": "NUMBERS", "NUMBERS": "NUMBERS",
    "EA": "EACH", "EACH": "EACH", "PC": "EACH", "PCS": "EACH", "PIECE": "EACH", "PIECES": "EACH",
    "LTR": "LITER", "LTRS": "LITER", "LITRE": "LITER", "LITRES": "LITER", "L": "LITER", "LITER": "LITER",
    "SET": "SET", "SETS": "SET",
    "ROLL": "ROLL", "ROLLS": "ROLL",
    "BOX": "BOX", "BOXES": "BOX",
    "PAIR": "PAIR", "PAIRS": "PAIR",
    "TON": "TON", "TONNE": "TON", "TONNES": "TON", "MT.": "TON",
    "SQM": "SQUARE METER", "SQ.M": "SQUARE METER", "SQ M": "SQUARE METER",
    "CUM": "CUBIC METER", "CU.M": "CUBIC METER",
}

# --- Common technical abbreviations ---------------------------------------------
ABBREVIATION_MAP: dict[str, str] = {
    "CS": "CARBON STEEL", "C.S": "CARBON STEEL", "C S": "CARBON STEEL",
    "SS": "STAINLESS STEEL", "S.S": "STAINLESS STEEL", "S S": "STAINLESS STEEL",
    "MS": "MILD STEEL", "M.S": "MILD STEEL",
    "GI": "GALVANIZED IRON", "G.I": "GALVANIZED IRON",
    "CI": "CAST IRON", "C.I": "CAST IRON",
    "AL": "ALUMINIUM", "ALU": "ALUMINIUM",
    "GR": "GRADE", "GRD": "GRADE",
    "DIA": "DIAMETER", "DIAM": "DIAMETER",
    "IND": "INDUSTRIAL",
    "LUB": "LUBRICANT", "LUBE": "LUBRICANT",
    "HEX": "HEXAGONAL", "HX": "HEXAGONAL",
    "SCH": "SCHEDULE",
    "SEAMLESS": "SEAMLESS", "SMLS": "SEAMLESS",
    "WLD": "WELDED", "ERW": "ELECTRIC RESISTANCE WELDED",
    "ASTM": "ASTM", "ANSI": "ANSI", "API": "API", "BS": "BS", "DIN": "DIN", "IS": "IS",
    "NB": "NOMINAL BORE", "OD": "OUTER DIAMETER", "ID": "INNER DIAMETER",
    "PN": "PRESSURE NOMINAL", "WT": "WALL THICKNESS",
}

# Nominal pipe size (DN) -> nominal inch size, used to line up "DN100" with '4"' / "4 inch".
DN_TO_INCH: dict[str, str] = {
    "DN8": "1/4IN", "DN10": "3/8IN", "DN15": "1/2IN", "DN20": "3/4IN", "DN25": "1IN",
    "DN32": "1.25IN", "DN40": "1.5IN", "DN50": "2IN", "DN65": "2.5IN", "DN80": "3IN",
    "DN100": "4IN", "DN125": "5IN", "DN150": "6IN", "DN200": "8IN", "DN250": "10IN",
    "DN300": "12IN",
}

_CATEGORY_SINGULAR_OVERRIDES = {
    "PIPES": "PIPE", "VALVES": "VALVE", "FLANGES": "FLANGE", "BEARINGS": "BEARING",
    "GASKETS": "GASKET", "FASTENERS": "FASTENER", "CABLES": "CABLE", "MOTORS": "MOTOR",
    "PUMPS": "PUMP", "LUBRICANTS": "LUBRICANT", "TRANSFORMERS": "TRANSFORMER",
    "CHEMICALS": "CHEMICAL",
}

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[.,;:_/\\]+")
_DIMENSION_INCH_RE = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:"|inch|inches|in\b)', re.IGNORECASE
)
_DN_RE = re.compile(r"\bDN\s?-?(\d{1,4})\b", re.IGNORECASE)


def basic_clean(text: str | None) -> str:
    """Uppercase, collapse whitespace, strip stray punctuation while keeping meaningful separators."""
    if not text:
        return ""
    t = text.strip().upper()
    t = t.replace('"', ' INCH ')
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t)
    return t.strip()


def _normalize_dimensions(text: str) -> str:
    """Rewrite inch / DN dimensional notations into one canonical token, e.g. '4IN'."""

    def _inch_sub(match: re.Match) -> str:
        value = match.group(1)
        return f"{value}IN"

    text = _DIMENSION_INCH_RE.sub(_inch_sub, text)

    def _dn_sub(match: re.Match) -> str:
        key = f"DN{match.group(1)}"
        return DN_TO_INCH.get(key, key)

    text = _DN_RE.sub(_dn_sub, text)
    return text


def _expand_abbreviations(text: str) -> str:
    tokens = text.split(" ")
    expanded: list[str] = []
    i = 0
    # try two-word abbreviations first (e.g. "C S" -> already merged by punctuation cleanup)
    while i < len(tokens):
        token = tokens[i]
        if token in ABBREVIATION_MAP:
            expanded.append(ABBREVIATION_MAP[token])
        else:
            expanded.append(token)
        i += 1
    return " ".join(expanded)


def normalize_uom(uom: str | None) -> str:
    cleaned = basic_clean(uom)
    return UOM_MAP.get(cleaned, cleaned)


def normalize_category(category: str | None) -> str:
    cleaned = basic_clean(category)
    cleaned = _expand_abbreviations(cleaned)
    if cleaned in _CATEGORY_SINGULAR_OVERRIDES:
        return _CATEGORY_SINGULAR_OVERRIDES[cleaned]
    return cleaned


def normalize_description(description: str | None) -> str:
    cleaned = basic_clean(description)
    cleaned = _normalize_dimensions(cleaned)
    cleaned = _expand_abbreviations(cleaned)
    return cleaned


def normalize_specification(specification: str | None) -> str:
    cleaned = basic_clean(specification)
    cleaned = _normalize_dimensions(cleaned)
    cleaned = _expand_abbreviations(cleaned)
    return cleaned


def normalize_material_type(material_type: str | None) -> str:
    cleaned = basic_clean(material_type)
    return _expand_abbreviations(cleaned)
