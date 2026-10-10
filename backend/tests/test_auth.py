from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_register_validation():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "12345678",
        },
    )

    assert response.status_code == 422


def test_login_validation():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "not-an-email",
            "password": "12345678",
        },
    )

    assert response.status_code == 422


def test_protected_endpoint_without_token():
    response = client.get(
        "/api/v1/auth/me"
    )

    assert response.status_code == 401


def test_protected_user_endpoint_without_token():
    response = client.get(
        "/api/v1/users/me"
    )

    assert response.status_code == 401