"""Huquqiy rozilik (legal consent): qabulni yozib qo'yish va o'z qabullarini
ro'yxatlash. Har qabul alohida audit qatori."""

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def test_record_consent(client: TestClient) -> None:
    user = _register(client, "consenter@example.com")
    resp = client.post(
        "/api/v1/legal/consent",
        headers={"Authorization": f"Bearer {user}"},
        json={"document_type": "terms", "version": "2026-07-01"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["document_type"] == "terms"
    assert body["version"] == "2026-07-01"
    assert body["accepted_at"] is not None


def test_consent_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/legal/consent",
        json={"document_type": "privacy", "version": "1.0"},
    )
    assert resp.status_code == 401


def test_list_my_consents(client: TestClient) -> None:
    user = _register(client, "consenter@example.com")
    headers = {"Authorization": f"Bearer {user}"}

    client.post(
        "/api/v1/legal/consent",
        headers=headers,
        json={"document_type": "terms", "version": "1.0"},
    )
    client.post(
        "/api/v1/legal/consent",
        headers=headers,
        json={"document_type": "public_offer", "version": "1.0"},
    )

    listing = client.get("/api/v1/legal/consents", headers=headers)
    assert listing.status_code == 200
    body = listing.json()
    assert len(body) == 2
    doc_types = {c["document_type"] for c in body}
    assert doc_types == {"terms", "public_offer"}


def test_consents_are_per_user(client: TestClient) -> None:
    a = _register(client, "usera@example.com")
    b = _register(client, "userb@example.com")

    client.post(
        "/api/v1/legal/consent",
        headers={"Authorization": f"Bearer {a}"},
        json={"document_type": "auction_rules", "version": "1.0"},
    )
    b_list = client.get("/api/v1/legal/consents", headers={"Authorization": f"Bearer {b}"})
    assert b_list.json() == []
