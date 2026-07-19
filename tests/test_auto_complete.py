"""Auto-complete worker: muddati o'tgan hold avtomatik capture qilinadi."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import OrderStatus, PaymentStatus
from app.models.order import Order
from app.models.payment import Payment
from app.services.auto_complete import auto_complete_due_orders


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return login.json()["access_token"]


def _order_with_hold(client: TestClient, seller: str, buyer: str, idem: str) -> tuple[int, int]:
    item = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller}"},
        json={"title": "Tripod", "condition": "used", "starting_price": "10000"},
    )
    now = datetime.now(UTC)
    auction = client.post(
        "/api/v1/auctions",
        headers={"Authorization": f"Bearer {seller}"},
        json={
            "item_id": item.json()["id"],
            "start_time": (now - timedelta(minutes=1)).isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "minimum_bid_increment": "1000",
        },
    )
    aid = auction.json()["id"]
    client.post(
        f"/api/v1/bids/{aid}",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"amount": "12000"},
    )
    client.post(f"/api/v1/auctions/{aid}/close", headers={"Authorization": f"Bearer {seller}"})
    order = client.get("/api/v1/orders/buyer", headers={"Authorization": f"Bearer {buyer}"}).json()[
        0
    ]
    hold = client.post(
        "/api/v1/payments/holds",
        headers={"Authorization": f"Bearer {buyer}"},
        json={"order_id": order["id"], "idempotency_key": idem, "provider": "mock"},
    )
    return order["id"], hold.json()["id"]


def test_auto_complete_captures_due_hold(client: TestClient, db_session: Session) -> None:
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order_id, payment_id = _order_with_hold(client, seller, buyer, "auto-hold-0001")

    # auto_complete_at ni o'tmishga suramiz — muddat o'tgan holatni simulyatsiya.
    order = db_session.get(Order, order_id)
    order.auto_complete_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    done = auto_complete_due_orders(db_session)
    assert done == 1

    db_session.expire_all()
    assert db_session.get(Payment, payment_id).status == PaymentStatus.RELEASED
    assert db_session.get(Order, order_id).status == OrderStatus.COMPLETED


def test_auto_complete_skips_future_hold(client: TestClient, db_session: Session) -> None:
    """auto_complete_at hali kelmagan order tegilmaydi."""
    seller = _register_and_login(client, "seller@example.com")
    buyer = _register_and_login(client, "buyer@example.com")
    order_id, payment_id = _order_with_hold(client, seller, buyer, "auto-hold-0002")

    # auto_complete_at kelajakda (hold 72 soat o'rnatadi) — tegilmaydi.
    done = auto_complete_due_orders(db_session)
    assert done == 0

    db_session.expire_all()
    assert db_session.get(Payment, payment_id).status == PaymentStatus.HELD
    assert db_session.get(Order, order_id).status == OrderStatus.PICKUP_PENDING
