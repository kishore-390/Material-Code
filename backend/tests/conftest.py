import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.cpse import CPSE
from app.models.material import CPSEMaterial
from app.models.user import Role
from app.services import normalization
from app.services.code_generator import ensure_sequence
from app.workers import tasks as worker_tasks

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


@pytest.fixture(autouse=True)
def _no_real_celery_broker(monkeypatch):
    """
    The dev docker-compose stack runs a real Redis broker and a real Celery
    worker connected to the real development database. Without this fixture,
    any test that hits an endpoint calling `.delay()` (or, for the batch
    settlement chord, `_dispatch_batch_chord`) would successfully enqueue
    work onto that real broker against the wrong database. Every such call
    site already has a try/except around it for "no broker reachable" that
    falls back to running the work inline, synchronously, against the same
    test db session - this fixture just applies that globally so no test can
    accidentally reach the real broker/worker.
    """

    def _raise(*_args, **_kwargs):
        raise RuntimeError("simulated: no broker reachable in tests")

    monkeypatch.setattr(worker_tasks.ai_analysis, "delay", _raise)
    monkeypatch.setattr(worker_tasks.bulk_ai_analysis, "delay", _raise)
    monkeypatch.setattr(worker_tasks.run_source_full_sync, "delay", _raise)
    monkeypatch.setattr(worker_tasks.run_source_incremental_sync, "delay", _raise)

    from app.connectors import sync_engine

    monkeypatch.setattr(sync_engine, "_dispatch_batch_chord", _raise)


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
    for name in ("ADMIN", "MATERIAL_EXPERT", "REVIEWER", "VIEWER"):
        role = Role(name=name, description=name.title())
        db_session.add(role)
        roles[name] = role
    cpse = CPSE(code="IOCL", name="Indian Oil Corporation Limited", sector="Oil & Gas")
    db_session.add(cpse)
    db_session.commit()
    return {"roles": roles, "cpse": cpse}


def register_and_login(client, username, role_name, cpse_code=None):
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "full_name": username.title(),
        "password": "Password@1",
        "role_name": role_name,
    }
    if cpse_code:
        payload["cpse_code"] = cpse_code
    client.post("/api/auth/register", json=payload)
    login = client.post("/api/auth/login", json={"username": username, "password": "Password@1"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_cpse(db_session, code: str, name: str, sector: str = "Oil & Gas") -> CPSE:
    cpse = db_session.query(CPSE).filter(CPSE.code == code).first()
    if cpse:
        return cpse
    cpse = CPSE(code=code, name=name, sector=sector)
    db_session.add(cpse)
    db_session.commit()
    return cpse


def create_cpse_material(
    db_session,
    cpse: CPSE,
    *,
    code: str,
    description: str,
    classification: str,
    uom: str,
    specification: str | None = None,
    material_type: str | None = None,
    material_grade: str | None = None,
    dimensions: str | None = None,
    standard: str | None = None,
    function: str | None = None,
    manufacturer: str | None = None,
    criticality: str = "UNSPECIFIED",
    packaging: str | None = None,
) -> CPSEMaterial:
    """
    Materials never arrive via a manual-entry API in the new architecture -
    only through app.connectors.sync_engine. Tests that need a CPSEMaterial
    row to exist insert it directly, exactly mirroring what
    sync_engine._upsert_material would have produced from a synced record.
    """
    material = CPSEMaterial(
        cpse_id=cpse.id,
        original_material_code=code,
        original_description=description,
        normalized_description=normalization.normalize_description(description),
        technical_specification=specification,
        normalized_specification=normalization.normalize_specification(specification),
        classification=classification,
        normalized_classification=normalization.normalize_classification(classification),
        uom=uom,
        normalized_uom=normalization.normalize_uom(uom),
        material_type=material_type,
        material_grade=material_grade,
        dimensions=dimensions,
        standard=standard,
        function=function,
        manufacturer=manufacturer,
        criticality=criticality,
        packaging=packaging,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)
    return material
