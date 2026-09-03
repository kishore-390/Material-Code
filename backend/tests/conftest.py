import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.cpse import CPSEOrganization
from app.models.user import Role
from app.services.code_generator import ensure_sequence

BASE_URL, _, _ = settings.DATABASE_URL.rpartition("/")
TEST_DATABASE_URL = f"{BASE_URL}/material_harmonization_test"
ADMIN_DATABASE_URL = f"{BASE_URL}/postgres"


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    admin_engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'material_harmonization_test'")
        ).first()
        if not exists:
            conn.execute(text("CREATE DATABASE material_harmonization_test"))
    admin_engine.dispose()

    engine = create_engine(TEST_DATABASE_URL, future=True)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)

    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with session_local() as db:
        ensure_sequence(db)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(_test_database):
    session_local = sessionmaker(bind=_test_database, autoflush=False, autocommit=False, future=True)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        # Tests commit for real (endpoints call db.commit()), so reset state between tests
        # by truncating everything rather than relying on a rollback-able transaction.
        with _test_database.connect() as conn:
            table_names = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
            conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
            conn.commit()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_roles_and_cpse(db_session):
    roles = {}
    for name in ("ADMIN", "MATERIAL_EXPERT", "CPSE_USER", "VIEWER"):
        role = Role(name=name, description=name.title())
        db_session.add(role)
        roles[name] = role
    cpse = CPSEOrganization(code="IOCL", name="Indian Oil Corporation Limited", sector="Oil & Gas")
    db_session.add(cpse)
    db_session.commit()
    return {"roles": roles, "cpse": cpse}
