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


def test_admin_can_create_organization_and_it_appears_immediately(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "admin_org_tester", "ADMIN")

    create_response = client.post(
        "/api/cpse",
        data={"code": "gail", "name": "GAIL (India) Limited", "sector": "Oil & Gas", "description": "Natural gas"},
        headers=headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["code"] == "GAIL"
    assert body["is_active"] is True

    listing = client.get("/api/cpse", headers=headers)
    codes = [c["code"] for c in listing.json()]
    assert "GAIL" in codes
    assert "IOCL" in codes  # pre-existing org untouched


def test_non_admin_cannot_create_or_edit_organization(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "cpse_org_tester", "CPSE_USER", "IOCL")
    create_response = client.post(
        "/api/cpse", data={"code": "BHEL", "name": "Bharat Heavy Electricals"}, headers=headers
    )
    assert create_response.status_code == 403

    cpse_id = str(seed_roles_and_cpse["cpse"].id)
    update_response = client.put(f"/api/cpse/{cpse_id}", data={"name": "Renamed"}, headers=headers)
    assert update_response.status_code == 403

    status_response = client.patch(f"/api/cpse/{cpse_id}/status", json={"is_active": False}, headers=headers)
    assert status_response.status_code == 403


def test_admin_can_update_and_deactivate_organization(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "admin_status_tester", "ADMIN")
    cpse_id = str(seed_roles_and_cpse["cpse"].id)

    update_response = client.put(
        f"/api/cpse/{cpse_id}", data={"sector": "Refining & Marketing"}, headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["sector"] == "Refining & Marketing"

    status_response = client.patch(f"/api/cpse/{cpse_id}/status", json={"is_active": False}, headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False


def test_new_organization_usable_for_upload_without_code_changes(client, seed_roles_and_cpse):
    admin_headers = _register_and_login(client, "admin_bhel_tester", "ADMIN")
    create_response = client.post(
        "/api/cpse", data={"code": "BHEL", "name": "Bharat Heavy Electricals Limited"}, headers=admin_headers
    )
    assert create_response.status_code == 201

    bhel_user_headers = _register_and_login(client, "bhel_uploader", "CPSE_USER", "BHEL")
    material_response = client.post(
        "/api/materials",
        data={
            "material_code": "BHEL-TURB-0001",
            "description": "Steam Turbine Blade",
            "category": "Turbines",
            "uom": "Nos",
            "cpse_code": "BHEL",
        },
        headers=bhel_user_headers,
    )
    assert material_response.status_code == 201
    assert material_response.json()["cpse"]["code"] == "BHEL"


def test_cpse_user_cannot_view_other_org_upload_history(client, seed_roles_and_cpse):
    admin_headers = _register_and_login(client, "admin_ongc_tester", "ADMIN")
    client.post("/api/cpse", data={"code": "ONGC", "name": "Oil and Natural Gas Corporation"}, headers=admin_headers)

    iocl_headers = _register_and_login(client, "iocl_upload_history_tester", "CPSE_USER", "IOCL")
    ongc_id = next(c["id"] for c in client.get("/api/cpse", headers=admin_headers).json() if c["code"] == "ONGC")

    response = client.get(f"/api/cpse/{ongc_id}/uploads", headers=iocl_headers)
    assert response.status_code == 403


def test_bulk_validate_with_organization_creates_upload_batch(client, seed_roles_and_cpse):
    import io

    headers = _register_and_login(client, "iocl_bulk_tester", "CPSE_USER", "IOCL")
    cpse_id = str(seed_roles_and_cpse["cpse"].id)

    csv_content = (
        "material_code,description,specification,category,uom,manufacturer,brand,material_type,image\n"
        "IOCL-BULK-0001,Ball Valve,,Valves,Nos,,,,\n"
        "IOCL-BULK-0002,Gate Valve,,Valves,Nos,,,,\n"
    )
    files = {"file": ("materials_iocl.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    response = client.post(
        "/api/materials/bulk/validate", data={"cpse_id": cpse_id}, files=files, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["upload_batch_id"] is not None
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 2
    # no "cpse" column needed - the organization dropdown supplies it
    assert all(row["data"]["cpse"] == "IOCL" for row in body["rows"])

    upload_response = client.get(f"/api/uploads/{body['upload_batch_id']}", headers=headers)
    assert upload_response.status_code == 200
    assert upload_response.json()["status"] == "VALIDATING"
    assert upload_response.json()["cpse"]["code"] == "IOCL"


def test_bulk_validate_rejects_cross_org_cpse_user(client, seed_roles_and_cpse):
    import io

    admin_headers = _register_and_login(client, "admin_cross_org_tester", "ADMIN")
    client.post("/api/cpse", data={"code": "SAIL", "name": "Steel Authority of India"}, headers=admin_headers)
    sail_id = next(c["id"] for c in client.get("/api/cpse", headers=admin_headers).json() if c["code"] == "SAIL")

    iocl_headers = _register_and_login(client, "iocl_cross_org_tester", "CPSE_USER", "IOCL")
    files = {"file": ("m.csv", io.BytesIO(b"material_code,description,category,uom\nX,Y,Z,Nos\n"), "text/csv")}
    response = client.post(
        "/api/materials/bulk/validate", data={"cpse_id": sail_id}, files=files, headers=iocl_headers
    )
    assert response.status_code == 403


def test_bulk_import_transitions_batch_to_queued(client, seed_roles_and_cpse):
    import io

    headers = _register_and_login(client, "iocl_import_tester", "CPSE_USER", "IOCL")
    cpse_id = str(seed_roles_and_cpse["cpse"].id)
    csv_content = "material_code,description,category,uom\nIOCL-Q-0001,Test Item,Fasteners,Nos\n"
    files = {"file": ("m.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    validate_response = client.post(
        "/api/materials/bulk/validate", data={"cpse_id": cpse_id}, files=files, headers=headers
    )
    batch_token = validate_response.json()["batch_token"]
    upload_batch_id = validate_response.json()["upload_batch_id"]

    import_response = client.post(
        "/api/materials/bulk/import", data={"batch_token": batch_token}, headers=headers
    )
    assert import_response.status_code == 200
    body = import_response.json()
    assert body["upload_batch_id"] == upload_batch_id
    assert body["status"] in ("QUEUED", "COMPLETED", "PARTIAL")
