"""
Materials arrive only through synchronization now (spec section 2A/2B) -
there is no create/update/delete-by-user API surface left to test. These
tests exercise the read-only list/get/search/similar endpoints against
directly-inserted CPSEMaterial rows (standing in for what a real sync would
have produced).
"""
from tests.conftest import create_cpse_material, register_and_login


def test_list_materials_pagination(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "list_tester", "VIEWER")
    cpse = seed_roles_and_cpse["cpse"]
    for i in range(3):
        create_cpse_material(
            db_session, cpse, code=f"IOCL-LIST-{i:04d}", description="Test Item",
            classification="Fastener", uom="Nos",
        )

    response = client.get("/api/cpse-materials?page=1&page_size=2", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2


def test_get_material_detail_includes_attributes_and_active_mapping(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "detail_tester", "VIEWER")
    cpse = seed_roles_and_cpse["cpse"]
    material = create_cpse_material(
        db_session, cpse, code="IOCL-DETAIL-0001", description="Ball Valve", classification="Valve", uom="Nos",
    )

    response = client.get(f"/api/cpse-materials/{material.id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["original_material_code"] == "IOCL-DETAIL-0001"
    assert body["active_common_material"] is None
    assert body["attributes"] == []


def test_get_unknown_material_returns_404(client, seed_roles_and_cpse):
    import uuid

    headers = register_and_login(client, "unknown_tester", "VIEWER")
    response = client.get(f"/api/cpse-materials/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_search_finds_material_by_code_or_description(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "search_tester", "VIEWER")
    cpse = seed_roles_and_cpse["cpse"]
    create_cpse_material(
        db_session, cpse, code="IOCL-SEARCH-0001", description="Carbon Steel Seamless Pipe",
        classification="Pipe", uom="Meter",
    )

    response = client.get("/api/cpse-materials/search", params={"q": "IOCL-SEARCH-0001"}, headers=headers)
    assert response.status_code == 200
    codes = {m["original_material_code"] for m in response.json()}
    assert "IOCL-SEARCH-0001" in codes


def test_filter_by_cpse_and_classification(client, db_session, seed_roles_and_cpse):
    headers = register_and_login(client, "filter_tester", "VIEWER")
    cpse = seed_roles_and_cpse["cpse"]
    create_cpse_material(db_session, cpse, code="IOCL-F1", description="Item A", classification="Valve", uom="Nos")
    create_cpse_material(db_session, cpse, code="IOCL-F2", description="Item B", classification="Cable", uom="Meter")

    response = client.get("/api/cpse-materials", params={"classification": "Valve"}, headers=headers)
    items = response.json()["items"]
    assert all(i["classification"] == "Valve" for i in items)
    assert len(items) == 1
