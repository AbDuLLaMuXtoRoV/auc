"""Shikoyat (complaint): foydalanuvchi yaratadi, admin ro'yxatlaydi va
holatini o'zgartiradi. Oddiy foydalanuvchi ro'yxat/patch'ga kira olmaydi."""

from fastapi.testclient import TestClient

from tests.conftest import AuthenticatedUser


def _register(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def test_user_creates_complaint(client: TestClient) -> None:
    reporter = _register(client, "reporter@example.com")
    resp = client.post(
        "/api/v1/complaints",
        headers={"Authorization": f"Bearer {reporter}"},
        json={
            "target_type": "item",
            "target_id": 42,
            "reason": "Soxta tovar",
            "description": "Rasmga mos emas",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "open"
    assert body["target_type"] == "item"
    assert body["target_id"] == 42
    assert body["resolved_at"] is None


def test_non_admin_cannot_list_complaints(client: TestClient) -> None:
    reporter = _register(client, "reporter@example.com")
    resp = client.get("/api/v1/complaints", headers={"Authorization": f"Bearer {reporter}"})
    assert resp.status_code == 403


def test_admin_lists_and_filters_complaints(
    client: TestClient, test_admin: AuthenticatedUser
) -> None:
    reporter = _register(client, "reporter@example.com")
    client.post(
        "/api/v1/complaints",
        headers={"Authorization": f"Bearer {reporter}"},
        json={"target_type": "user", "target_id": 7, "reason": "Spam"},
    )

    all_list = client.get("/api/v1/complaints", headers=test_admin.headers)
    assert all_list.status_code == 200
    assert len(all_list.json()) == 1

    open_list = client.get("/api/v1/complaints?status=open", headers=test_admin.headers)
    assert len(open_list.json()) == 1

    resolved_list = client.get("/api/v1/complaints?status=resolved", headers=test_admin.headers)
    assert resolved_list.json() == []


def test_admin_resolves_complaint_sets_resolver(
    client: TestClient, test_admin: AuthenticatedUser
) -> None:
    reporter = _register(client, "reporter@example.com")
    created = client.post(
        "/api/v1/complaints",
        headers={"Authorization": f"Bearer {reporter}"},
        json={"target_type": "auction", "target_id": 3, "reason": "Shubhali"},
    )
    complaint_id = created.json()["id"]

    resolved = client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers=test_admin.headers,
        json={"status": "resolved"},
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["status"] == "resolved"
    assert body["resolved_by_id"] == test_admin.id
    assert body["resolved_at"] is not None


def test_non_admin_cannot_patch_complaint(client: TestClient) -> None:
    reporter = _register(client, "reporter@example.com")
    created = client.post(
        "/api/v1/complaints",
        headers={"Authorization": f"Bearer {reporter}"},
        json={"target_type": "message", "target_id": 1, "reason": "Haqorat"},
    )
    complaint_id = created.json()["id"]

    resp = client.patch(
        f"/api/v1/complaints/{complaint_id}",
        headers={"Authorization": f"Bearer {reporter}"},
        json={"status": "rejected"},
    )
    assert resp.status_code == 403
