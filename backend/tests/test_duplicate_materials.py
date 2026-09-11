import uuid

from app.ai.analyzer import analyze_material
from tests.conftest import create_cpse, create_cpse_material, register_and_login


def _make_harmonized_valve_pair(db_session, iocl, ongc):
    a = create_cpse_material(
        db_session, iocl, code="IOCL-1002", description="Carbon Steel Gate Valve",
        specification="API 600 Class 150", classification="Valve", uom="Nos",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC-2002", description="CS Gate Valve",
        specification="API 600 Class 150", classification="Valve", uom="Nos",
    )
    analyze_material(db_session, b.id)
    analyze_material(db_session, a.id)
    return a, b


def test_duplicate_total_matches_dashboard_kpi(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dup_kpi_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_harmonized_valve_pair(db_session, iocl, ongc)

    stats = client.get("/api/dashboard/statistics", headers=headers).json()
    dup = client.get("/api/harmonization/duplicates", headers=headers).json()

    assert dup["total_duplicates"] >= 1
    assert stats["duplicates_identified"] >= 1
    assert dup["common_materials_generated"] >= 1


def test_duplicate_list_returns_real_pair_data(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dup_pair_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_harmonized_valve_pair(db_session, iocl, ongc)

    dup = client.get("/api/harmonization/duplicates", headers=headers).json()
    assert dup["total"] == 1
    item = dup["items"][0]

    codes = {item["source_material"]["original_material_code"], item["matched_material"]["original_material_code"]}
    assert codes == {"IOCL-1002", "ONGC-2002"}
    assert item["common_material"]["common_code"].startswith("CM-")
    assert item["confidence_score"] is not None
    assert item["confidence_score"] > 0


def test_duplicate_search_finds_pair_by_code_or_description(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dup_search_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_harmonized_valve_pair(db_session, iocl, ongc)

    by_code = client.get("/api/harmonization/duplicates", params={"q": "IOCL-1002"}, headers=headers).json()
    assert by_code["total"] == 1

    no_match = client.get("/api/harmonization/duplicates", params={"q": "nonexistent-widget-zzz"}, headers=headers).json()
    assert no_match["total"] == 0


def test_duplicate_pair_detail_endpoint(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dup_detail_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")
    _make_harmonized_valve_pair(db_session, iocl, ongc)

    dup = client.get("/api/harmonization/duplicates", headers=headers).json()
    mapping_id = dup["items"][0]["mapping_id"]

    detail = client.get(f"/api/harmonization/pairs/{mapping_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["mapping_id"] == mapping_id
    assert body["breakdown"] is not None

    unknown = client.get(f"/api/harmonization/pairs/{uuid.uuid4()}", headers=headers)
    assert unknown.status_code == 404


def test_duplicate_empty_state_returns_zero_not_fake_data(client, seed_roles_and_cpse):
    headers = register_and_login(client, "dup_empty_admin", "ADMIN")
    dup = client.get("/api/harmonization/duplicates", headers=headers).json()
    assert dup["total"] == 0
    assert dup["total_duplicates"] == 0
    assert dup["common_materials_generated"] == 0
    assert dup["items"] == []


def test_technical_conflicts_view_lists_only_conflicted_mappings(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "dup_conflict_admin", "ADMIN")
    iocl = seed_roles_and_cpse["cpse"]
    ongc = create_cpse(db_session, "ONGC", "Oil and Natural Gas Corporation")

    a = create_cpse_material(
        db_session, iocl, code="IOCL-CONF-1", description="SS Bolt M10x50 SS304",
        classification="Fastener", uom="PC", material_grade="SS304",
    )
    b = create_cpse_material(
        db_session, ongc, code="ONGC-CONF-1", description="SS Bolt M10x50 SS316",
        classification="Fastener", uom="PC", material_grade="SS316",
    )
    analyze_material(db_session, b.id)
    analyze_material(db_session, a.id)

    conflicts = client.get("/api/harmonization/technical-conflicts", headers=headers).json()
    assert conflicts["total"] >= 1
    assert all(item["decision_status"] == "TECHNICAL_CONFLICT" for item in conflicts["items"])
