from tests.conftest import register_and_login


def test_register_with_unknown_cpse_code_fails(client, seed_roles_and_cpse):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "bad_cpse_user",
            "email": "bad_cpse@example.com",
            "full_name": "Bad Cpse",
            "password": "Password@1",
            "role_name": "VIEWER",
            "cpse_code": "DOES_NOT_EXIST",
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
            "role_name": "VIEWER",
        },
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["username"] == "test_user"
    assert body["role"]["name"] == "VIEWER"

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


def test_deactivated_user_cannot_login(client, db_session, seed_roles_and_cpse):
    from app.models.user import User

    register_and_login(client, "will_be_deactivated", "VIEWER")
    user = db_session.query(User).filter(User.username == "will_be_deactivated").first()
    user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/auth/login", json={"username": "will_be_deactivated", "password": "Password@1"}
    )
    assert response.status_code == 403
