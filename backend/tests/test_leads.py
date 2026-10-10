from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_leads_requires_authentication():
    response = client.get(
        "/api/v1/leads"
    )

    assert response.status_code == 401


def test_single_lead_requires_authentication():
    response = client.get(
        "/api/v1/leads/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 401


def test_delete_lead_requires_authentication():
    response = client.delete(
        "/api/v1/leads/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 401