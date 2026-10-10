from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_discovery_requires_authentication():
    response = client.post(
        "/api/v1/discovery/businesses",
        json={
            "country": "Pakistan",
            "state": "Punjab",
            "city": "Lahore",
            "industry": "restaurant",
            "limit": 10,
        },
    )

    assert response.status_code == 401


def test_discovery_validation_limit():
    response = client.post(
        "/api/v1/discovery/businesses",
        json={
            "country": "Pakistan",
            "state": "Punjab",
            "city": "Lahore",
            "industry": "restaurant",
            "limit": 101,
        },
    )

    assert response.status_code == 422


def test_discovery_validation_missing_city():
    response = client.post(
        "/api/v1/discovery/businesses",
        json={
            "country": "Pakistan",
            "state": "Punjab",
            "industry": "restaurant",
            "limit": 10,
        },
    )

    assert response.status_code == 422