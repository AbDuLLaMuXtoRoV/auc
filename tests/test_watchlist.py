"""Kuzatuv ro'yxati (watchlist): qo'shish idempotent (unique), o'chirish,
ro'yxatlash va foydalanuvchiga xoslik."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import AuthenticatedUser, create_auction, create_item


def _register(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return login.json()["access_token"]


def _auction(client: TestClient, seller: AuthenticatedUser) -> int:
    item = create_item(client, seller, title="Kuzatiladigan lot")
    auction = create_auction(client, seller, item["id"])
    return auction["id"]


def test_add_to_watchlist(client: TestClient, test_seller: AuthenticatedUser) -> None:
    auction_id = _auction(client, test_seller)
    watcher = _register(client, "watcher@example.com")

    resp = client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {watcher}"},
        json={"auction_id": auction_id},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["auction_id"] == auction_id


def test_add_missing_auction_404(client: TestClient) -> None:
    watcher = _register(client, "watcher@example.com")
    resp = client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {watcher}"},
        json={"auction_id": 99999},
    )
    assert resp.status_code == 404


def test_add_is_idempotent_unique(client: TestClient, test_seller: AuthenticatedUser) -> None:
    """Bir auksionni ikki marta qo'shish unique buzmaydi — bitta yozuv qoladi."""
    auction_id = _auction(client, test_seller)
    watcher = _register(client, "watcher@example.com")
    headers = {"Authorization": f"Bearer {watcher}"}

    first = client.post("/api/v1/watchlist", headers=headers, json={"auction_id": auction_id})
    second = client.post("/api/v1/watchlist", headers=headers, json={"auction_id": auction_id})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listing = client.get("/api/v1/watchlist", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_remove_from_watchlist(client: TestClient, test_seller: AuthenticatedUser) -> None:
    auction_id = _auction(client, test_seller)
    watcher = _register(client, "watcher@example.com")
    headers = {"Authorization": f"Bearer {watcher}"}

    client.post("/api/v1/watchlist", headers=headers, json={"auction_id": auction_id})
    removed = client.delete(f"/api/v1/watchlist/{auction_id}", headers=headers)
    assert removed.status_code == 204

    listing = client.get("/api/v1/watchlist", headers=headers)
    assert listing.json() == []


def test_remove_missing_returns_404(client: TestClient, test_seller: AuthenticatedUser) -> None:
    auction_id = _auction(client, test_seller)
    watcher = _register(client, "watcher@example.com")
    headers = {"Authorization": f"Bearer {watcher}"}

    resp = client.delete(f"/api/v1/watchlist/{auction_id}", headers=headers)
    assert resp.status_code == 404


def test_watchlist_is_per_user(
    client: TestClient, db_session: Session, test_seller: AuthenticatedUser
) -> None:
    """Bir foydalanuvchi kuzatuvi ikkinchisiga ko'rinmaydi."""
    auction_id = _auction(client, test_seller)
    a = _register(client, "usera@example.com")
    b = _register(client, "userb@example.com")

    client.post(
        "/api/v1/watchlist",
        headers={"Authorization": f"Bearer {a}"},
        json={"auction_id": auction_id},
    )
    b_list = client.get("/api/v1/watchlist", headers={"Authorization": f"Bearer {b}"})
    assert b_list.json() == []
