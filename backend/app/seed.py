"""
Minimal system bootstrap (spec section 43).

Run with:  docker compose exec backend python -m app.seed

Creates only what a fresh deployment needs to be usable at all: the four
RBAC roles and a single ADMIN login. It creates NO CPSEs, NO materials, and
NO common materials - the material master stays empty until real source
connectors (see app.connectors) are configured and synced. For a
demonstration environment with a seeded example source database, see
app.demo_seed instead - that is a deliberately separate, opt-in script so a
production deployment is never left with fake data pretending to be real.
"""
import logging

from app.core.security import hash_password
from app.db.base import Base  # noqa: F401 - ensures all models are registered
from app.db.session import SessionLocal, engine
from app.models.user import Role, User
from app.services.code_generator import ensure_sequence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

ROLES = [
    ("ADMIN", "Full system administration, connector configuration, thresholds and governance"),
    ("MATERIAL_EXPERT", "Reviews AI recommendations and approves/rejects/edits harmonization mappings"),
    ("REVIEWER", "Reviews pending validations and flags items for manual review, without final approval authority"),
    ("VIEWER", "Read-only dashboards and reports"),
]

USERS = [
    # username, email, full_name, password, role
    ("admin", "admin@material.gov.in", "System Administrator", "Admin@123", "ADMIN"),
]


def get_or_create_roles(db) -> dict[str, Role]:
    roles = {}
    for name, description in ROLES:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()
        roles[name] = role
    db.commit()
    return roles


def get_or_create_users(db, roles: dict[str, Role]) -> dict[str, User]:
    users = {}
    for username, email, full_name, password, role_name in USERS:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role_id=roles[role_name].id,
            )
            db.add(user)
            db.flush()
        users[username] = user
    db.commit()
    return users


def main() -> None:
    Base.metadata.create_all(bind=engine)  # safety net if migrations haven't run yet
    db = SessionLocal()
    try:
        ensure_sequence(db)
        roles = get_or_create_roles(db)
        users = get_or_create_users(db, roles)
        logger.info("Seeded %s roles, %s users. No CPSEs, materials, or common materials were created.", len(roles), len(users))

        logger.info("=" * 70)
        logger.info("ADMIN LOGIN CREDENTIALS")
        for username, _, full_name, password, role_name in USERS:
            logger.info("  %-14s / %-12s  (%s - %s)", username, password, full_name, role_name)
        logger.info("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
