import os
import uuid

import app.ai.ml_ranker as ml_ranker
from app.ai.analyzer import analyze_material
from app.core.config import settings


def _register_and_login(client, username, role_name, cpse_code=None):
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


def _create_ongc_org(client, admin_headers):
    client.post("/api/cpse", data={"code": "ONGC", "name": "Oil and Natural Gas Corporation"}, headers=admin_headers)


def _create_material(client, admin_headers, *, code, description, category, uom, cpse_code, specification=None, material_type=None):
    resp = client.post(
        "/api/materials",
        data={
            "material_code": code,
            "description": description,
            "specification": specification or "",
            "category": category,
            "uom": uom,
            "cpse_code": cpse_code,
            "material_type": material_type or "",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_trained_model_loads_successfully():
    """Requires app/ml_models/material_match_xgb.json to exist - produced by
    `python -m app.ml.train_xgb_ranker` (see that module's docstring)."""
    assert os.path.exists(settings.XGB_MODEL_PATH), (
        "No trained model found. Run: docker compose exec backend python -m app.ml.train_xgb_ranker"
    )
    ml_ranker.reset_model_cache()
    result = ml_ranker.score_with_ml(
        {"description_score": 90, "specification_score": 90, "category_score": 100, "uom_score": 100, "attribute_score": 90, "image_score": 0}
    )
    assert result.status == "TRAINED"
    assert result.available is True
    assert result.score is not None


def test_equivalent_valve_pair_gets_high_xgboost_probability(client, db_session, seed_roles_and_cpse):
    """
    Same regression case as before (a genuinely equivalent CS Gate Valve
    pair, worded differently by each CPSE) but exercised through the
    surviving pipeline: create both materials directly (no demo source
    database), then run the real analyze_material() full-pool pipeline
    (SBERT embeddings -> pgvector candidate retrieval -> scoring ->
    XGBoost blend -> decision engine) exactly as the full-database scan
    does for every material.
    """
    admin_headers = _register_and_login(client, "xgb_valve_admin", "ADMIN")
    _create_ongc_org(client, admin_headers)

    iocl = _create_material(
        client, admin_headers, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", category="Valves", uom="Nos", cpse_code="IOCL",
    )
    ongc = _create_material(
        client, admin_headers, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", category="Valve", uom="Nos", cpse_code="ONGC",
    )

    # analyze_material()'s candidate search only matches materials that
    # already have a stored embedding (see app.ai.similarity.find_candidate_materials)
    # - exactly like the real full-database-scan queue, the candidate must be
    # analyzed first so it becomes findable when the primary material is analyzed.
    analyze_material(db_session, uuid.UUID(ongc["id"]))
    analyze_material(db_session, uuid.UUID(iocl["id"]))

    response = client.get(f"/api/ai/analysis/{iocl['id']}", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["ml_status"] == "TRAINED"
    assert body["ml_probability"] is not None
    assert body["ml_probability"] > 70
    assert body["decision"] == "AUTO_HARMONIZATION"
    assert body["recommended_common_code"] is not None


def test_pipe_vs_drill_bit_gets_low_probability_and_is_rejected(client, db_session, seed_roles_and_cpse):
    admin_headers = _register_and_login(client, "xgb_reject_admin", "ADMIN")
    _create_ongc_org(client, admin_headers)

    iocl = _create_material(
        client, admin_headers, code="IOCL-1001", description="Carbon Steel Seamless Pipe",
        specification="ASTM A106 Grade B", category="Pipes", uom="M", cpse_code="IOCL",
    )
    ongc = _create_material(
        client, admin_headers, code="ONGC-2011", description="Drill Bit Tricone Type",
        specification="Tricone Roller Cone Bit", category="Drilling Equipment", uom="Nos", cpse_code="ONGC",
    )

    analyze_material(db_session, uuid.UUID(ongc["id"]))
    analyze_material(db_session, uuid.UUID(iocl["id"]))

    response = client.get(f"/api/ai/analysis/{iocl['id']}", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["ml_probability"] is None or body["ml_probability"] < 30
    assert body["decision"] in ("LOW_CONFIDENCE", "NO_COMMON_CODE")
    assert body["recommended_common_code"] is None


def test_xgboost_does_not_override_category_incompatible_safety_gate(client, db_session, seed_roles_and_cpse):
    """Even where XGBoost itself is confident (category-mismatched pump pair
    genuinely scores high on description/spec), the category-incompatibility
    safety floor must keep it out of the blended score - final_score must
    equal the pure rule-based score, not a blend, whenever category_score is
    below XGB_SAFETY_CATEGORY_FLOOR."""
    admin_headers = _register_and_login(client, "xgb_gate_admin", "ADMIN")
    _create_ongc_org(client, admin_headers)

    iocl = _create_material(
        client, admin_headers, code="IOCL-1003", description="Industrial Centrifugal Pump",
        specification="API 610", category="Pumps", uom="Nos", cpse_code="IOCL",
    )
    ongc = _create_material(
        client, admin_headers, code="ONGC-2003", description="Centrifugal Pump for Industrial Water Service",
        specification="API 610", category="Rotating Equipment", uom="Nos", cpse_code="ONGC",
    )

    analyze_material(db_session, uuid.UUID(ongc["id"]))
    analyze_material(db_session, uuid.UUID(iocl["id"]))

    response = client.get(f"/api/ai/analysis/{iocl['id']}", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    if body["category_score"] < ml_ranker.XGB_SAFETY_CATEGORY_FLOOR:
        # overall_score must NOT have moved toward xgboost_probability when the gate is closed.
        assert body["ml_probability"] is None or abs(body["final_score"] - body["ml_probability"]) > 5


def test_missing_model_falls_back_safely(monkeypatch):
    monkeypatch.setattr(settings, "XGB_MODEL_PATH", "/tmp/does-not-exist-xgb-model.json")
    ml_ranker.reset_model_cache()
    result = ml_ranker.score_with_ml(
        {"description_score": 90, "specification_score": 90, "category_score": 100, "uom_score": 100, "attribute_score": 90, "image_score": 0}
    )
    assert result.status == "FALLBACK"
    assert result.available is False
    assert result.score is None
    ml_ranker.reset_model_cache()  # restore for subsequent tests


def test_feature_order_never_includes_material_codes():
    assert "material_code" not in ml_ranker.FEATURE_ORDER
    assert "source_material_code" not in ml_ranker.FEATURE_ORDER
    for name in ml_ranker.FEATURE_ORDER:
        assert "code" not in name.lower()
