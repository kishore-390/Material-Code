from tests.conftest import register_and_login


def test_admin_can_create_cpse_and_it_appears_immediately(client, seed_roles_and_cpse):
    headers = register_and_login(client, "admin_org_tester", "ADMIN")

    create_response = client.post(
        "/api/cpse",
        json={"code": "gail", "name": "GAIL (India) Limited", "sector": "Oil & Gas"},
        headers=headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["code"] == "GAIL"
    assert body["is_active"] is True

    listing = client.get("/api/cpse", headers=headers)
    codes = [c["code"] for c in listing.json()]
    assert "GAIL" in codes
    assert "IOCL" in codes  # pre-existing CPSE untouched


def test_non_admin_cannot_create_or_edit_cpse(client, seed_roles_and_cpse):
    headers = register_and_login(client, "viewer_org_tester", "VIEWER")
    create_response = client.post("/api/cpse", json={"code": "BHEL", "name": "Bharat Heavy Electricals"}, headers=headers)
    assert create_response.status_code == 403

    cpse_id = str(seed_roles_and_cpse["cpse"].id)
    update_response = client.put(f"/api/cpse/{cpse_id}", json={"name": "Renamed"}, headers=headers)
    assert update_response.status_code == 403

    status_response = client.patch(f"/api/cpse/{cpse_id}/status", json={"is_active": False}, headers=headers)
    assert status_response.status_code == 403


def test_admin_can_update_and_deactivate_cpse(client, seed_roles_and_cpse):
    headers = register_and_login(client, "admin_status_tester", "ADMIN")
    cpse_id = str(seed_roles_and_cpse["cpse"].id)

    update_response = client.put(f"/api/cpse/{cpse_id}", json={"sector": "Refining & Marketing"}, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json()["sector"] == "Refining & Marketing"

    status_response = client.patch(f"/api/cpse/{cpse_id}/status", json={"is_active": False}, headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False


def test_cpse_stats_reflect_zero_materials_for_new_cpse(client, seed_roles_and_cpse):
    headers = register_and_login(client, "admin_stats_tester", "ADMIN")
    create_response = client.post("/api/cpse", json={"code": "SAIL", "name": "Steel Authority of India"}, headers=headers)
    cpse_id = create_response.json()["id"]

    stats = client.get(f"/api/cpse/{cpse_id}", headers=headers).json()
    assert stats["total_materials"] == 0
    assert stats["common_materials"] == 0
    assert stats["pending_mappings"] == 0
    assert stats["synchronization_status"] == "NEVER_SYNCED"
