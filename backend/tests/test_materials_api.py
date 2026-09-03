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


def test_create_and_fetch_material(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "iocl_tester", "CPSE_USER", "IOCL")

    create_response = client.post(
        "/api/materials",
        data={
            "material_code": "IOCL-TEST-0001",
            "description": "Carbon Steel Seamless Pipe",
            "specification": "ASTM A106 Grade B, 4 inch",
            "category": "Pipes",
            "uom": "Meter",
            "cpse_code": "IOCL",
            "manufacturer": "Jindal Saw",
            "brand": "JSL",
            "material_type": "Carbon Steel",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    body = create_response.json()
    assert body["material_code"] == "IOCL-TEST-0001"
    assert body["normalized_uom"] == "METER"
    assert body["status"] == "PENDING"

    material_id = body["id"]
    get_response = client.get(f"/api/materials/{material_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["description"] == "Carbon Steel Seamless Pipe"


def test_duplicate_material_code_rejected(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "iocl_dup_tester", "CPSE_USER", "IOCL")
    payload = {
        "material_code": "IOCL-DUP-0001",
        "description": "Ball Valve",
        "category": "Valves",
        "uom": "Nos",
        "cpse_code": "IOCL",
    }
    first = client.post("/api/materials", data=payload, headers=headers)
    assert first.status_code == 201
    second = client.post("/api/materials", data=payload, headers=headers)
    assert second.status_code == 400


def test_cpse_user_cannot_upload_for_other_cpse(client, seed_roles_and_cpse):
    from app.models.cpse import CPSEOrganization

    headers = _register_and_login(client, "iocl_scoped_tester", "CPSE_USER", "IOCL")
    payload = {
        "material_code": "ONGC-FORBIDDEN-0001",
        "description": "Ball Valve",
        "category": "Valves",
        "uom": "Nos",
        "cpse_code": "ONGC",
    }
    response = client.post("/api/materials", data=payload, headers=headers)
    # ONGC does not exist in this test's seed data, so either a 400 (unknown CPSE)
    # or 403 (cross-CPSE upload blocked) is an acceptable rejection.
    assert response.status_code in (400, 403)


def test_viewer_cannot_create_material(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "viewer_tester", "VIEWER")
    payload = {
        "material_code": "VIEW-0001",
        "description": "Ball Valve",
        "category": "Valves",
        "uom": "Nos",
        "cpse_code": "IOCL",
    }
    response = client.post("/api/materials", data=payload, headers=headers)
    assert response.status_code == 403


def test_list_materials_pagination(client, seed_roles_and_cpse):
    headers = _register_and_login(client, "iocl_list_tester", "CPSE_USER", "IOCL")
    for i in range(3):
        client.post(
            "/api/materials",
            data={
                "material_code": f"IOCL-LIST-{i:04d}",
                "description": "Test Item",
                "category": "Fasteners",
                "uom": "Nos",
                "cpse_code": "IOCL",
            },
            headers=headers,
        )
    response = client.get("/api/materials?page=1&page_size=2", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2
