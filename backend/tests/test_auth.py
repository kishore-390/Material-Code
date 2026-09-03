def test_register_cpse_user_requires_cpse_code(client, seed_roles_and_cpse):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "no_cpse_user",
            "email": "no_cpse@example.com",
            "full_name": "No Cpse",
            "password": "Password@1",
            "role_name": "CPSE_USER",
        },
    )
    assert response.status_code == 400


def test_register_and_login_success(client, seed_roles_and_cpse):
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "test_user",
            "email": "test_user@example.com",
            "full_name": "Test User",
            "password": "Password@1",
            "role_name": "CPSE_USER",
            "cpse_code": "IOCL",
        },
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["username"] == "test_user"
    assert body["role"]["name"] == "CPSE_USER"

    login_response = client.post(
        "/api/auth/login", json={"username": "test_user", "password": "Password@1"}
    )
    assert login_response.status_code == 200
    token_payload = login_response.json()
    assert "access_token" in token_payload

    me_response = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token_payload['access_token']}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "test_user"


def test_login_with_wrong_password_fails(client, seed_roles_and_cpse):
    client.post(
        "/api/auth/register",
        json={
            "username": "wrongpass_user",
            "email": "wrongpass@example.com",
            "full_name": "Wrong Pass",
            "password": "Password@1",
            "role_name": "VIEWER",
        },
    )
    response = client.post(
        "/api/auth/login", json={"username": "wrongpass_user", "password": "IncorrectPassword"}
    )
    assert response.status_code == 401
