"""
Common Material Code generator (spec section 11).

Format: <MATERIAL TYPE SHORT CODE>-<CATEGORY SHORT CODE>-<SEQUENTIAL ID>
e.g. CS-PIPE-00124, BALL-VALVE-00087, IND-LUBE-00045, SS-FLANGE-00231

The sequential component comes from a PostgreSQL sequence
(`common_material_code_seq`, created by the initial Alembic migration) so
concurrent workers can never collide -- nextval() is atomic at the
database level, which is what guarantees uniqueness under load.
"""
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

TYPE_SHORT_MAP: dict[str, str] = {
    "CARBON STEEL": "CS",
    "STAINLESS STEEL": "SS",
    "MILD STEEL": "MS",
    "CAST IRON": "CI",
    "GALVANIZED IRON": "GI",
    "ALUMINIUM": "AL",
    "ALUMINUM": "AL",
    "BRONZE": "BRZ",
    "COPPER": "CU",
    "RUBBER": "RUB",
    "INDUSTRIAL": "IND",
    "BALL": "BALL",
    "GATE": "GATE",
    "GLOBE": "GLOBE",
    "CHECK": "CHK",
    "BUTTERFLY": "BFLY",
}

CATEGORY_SHORT_MAP: dict[str, str] = {
    "PIPE": "PIPE",
    "VALVE": "VALVE",
    "FLANGE": "FLANGE",
    "BEARING": "BEARING",
    "GASKET": "GASKET",
    "FASTENER": "FSTNR",
    "CABLE": "CABLE",
    "MOTOR": "MOTOR",
    "PUMP": "PUMP",
    "LUBRICANT": "LUBE",
    "TRANSFORMER": "XFMR",
    "CHEMICAL": "CHEM",
}

_NON_ALPHA_RE = re.compile(r"[^A-Z0-9]+")


def _short_code(value: str | None, fallback_len: int, lookup: dict[str, str]) -> str:
    if not value:
        return "GEN"
    cleaned = value.strip().upper()
    if cleaned in lookup:
        return lookup[cleaned]
    first_word = cleaned.split(" ")[0]
    if first_word in lookup:
        return lookup[first_word]
    compact = _NON_ALPHA_RE.sub("", cleaned)
    return compact[:fallback_len] or "GEN"


def ensure_sequence(db: Session) -> None:
    db.execute(text("CREATE SEQUENCE IF NOT EXISTS common_material_code_seq START WITH 1 INCREMENT BY 1"))
    db.commit()


def generate_common_code(db: Session, material_type: str | None, category: str | None) -> str:
    """Transaction-safe unique code generation using a DB sequence."""
    type_code = _short_code(material_type, 4, TYPE_SHORT_MAP)
    category_code = _short_code(category, 6, CATEGORY_SHORT_MAP)
    seq_value = db.execute(text("SELECT nextval('common_material_code_seq')")).scalar_one()
    return f"{type_code}-{category_code}-{int(seq_value):05d}"
