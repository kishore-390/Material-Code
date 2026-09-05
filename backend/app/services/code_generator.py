"""
National Common Material Code generator.

Format: CM-XXXXXX (CM = Common Material, six-digit zero-padded sequence),
e.g. CM-000001, CM-000184. The code is deliberately neutral - it never
encodes any single CPSE's own material type/category vocabulary, since it
represents the harmonized national identity for the group, not a renamed
CPSE code.

The sequential component comes from a PostgreSQL sequence
(`common_material_code_seq`, created by the initial Alembic migration) so
concurrent workers can never collide - nextval() is atomic at the
database level, which is what guarantees uniqueness under load.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def ensure_sequence(db: Session) -> None:
    db.execute(text("CREATE SEQUENCE IF NOT EXISTS common_material_code_seq START WITH 1 INCREMENT BY 1"))
    db.commit()


def generate_common_code(db: Session) -> str:
    """Transaction-safe unique code generation using a DB sequence."""
    seq_value = db.execute(text("SELECT nextval('common_material_code_seq')")).scalar_one()
    return f"CM-{int(seq_value):06d}"
