from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_website_check_requires_authentication():
    response = client.post(
        "/api/v1/leads/"
        "00000000-0000-0000-0000-000000000000/"
        "website-check"
    )

    assert response.status_code == 401


def test_website_batch_requires_authentication():
    response = client.post(
        "/api/v1/leads/website-check/batch",
        json={
            "lead_ids": [
                "00000000-0000-0000-0000-000000000000"
            ]
        },
    )

    assert response.status_code == 401