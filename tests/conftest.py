from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import base  # noqa: F401
from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
TEST_PASSWORD = "Password1"


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    email: str
    password: str
    access_token: str
    refresh_token: str
    headers: dict[str, str]


@pytest.fixture
def db_session() -> Generator[Session]:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def register_user(
    client: TestClient,
    *,
    email: str,
    password: str = TEST_PASSWORD,
    full_name: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name or email.split("@")[0],
        },
    )
    assert response.status_code == 201
    return response.json()


def login_user(
    client: TestClient,
    *,
    email: str,
    password: str = TEST_PASSWORD,
) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def create_user(
    client: TestClient,
    db_session: Session,
    *,
    email: str,
    role: UserRole = UserRole.USER,
    password: str = TEST_PASSWORD,
) -> AuthenticatedUser:
    registered_user = register_user(client, email=email, password=password)
    if role != UserRole.USER:
        user = UserRepository(db_session).get_by_email(email)
        assert user is not None
        UserRepository(db_session).set_role(user, role)

    token_payload = login_user(client, email=email, password=password)
    return AuthenticatedUser(
        id=registered_user["id"],
        email=email,
        password=password,
        access_token=token_payload["access_token"],
        refresh_token=token_payload["refresh_token"],
        headers=auth_headers(token_payload["access_token"]),
    )


def create_item(
    client: TestClient,
    seller: AuthenticatedUser,
    *,
    title: str = "Test item",
    starting_price: str = "10.00",
    category_id: int | None = None,
) -> dict:
    payload = {
        "title": title,
        "condition": "used",
        "starting_price": starting_price,
    }
    if category_id is not None:
        payload["category_id"] = category_id
    response = client.post("/api/v1/items", headers=seller.headers, json=payload)
    assert response.status_code == 201
    return response.json()


def create_auction(
    client: TestClient,
    seller: AuthenticatedUser,
    item_id: int,
    *,
    start_delta: timedelta = -timedelta(minutes=1),
    end_delta: timedelta = timedelta(days=1),
    minimum_bid_increment: str = "1.00",
    reserve_price: str | None = None,
) -> dict:
    now = datetime.now(UTC)
    payload = {
        "item_id": item_id,
        "start_time": (now + start_delta).isoformat(),
        "end_time": (now + end_delta).isoformat(),
        "minimum_bid_increment": minimum_bid_increment,
    }
    if reserve_price is not None:
        payload["reserve_price"] = reserve_price
    response = client.post("/api/v1/auctions", headers=seller.headers, json=payload)
    assert response.status_code == 201
    return response.json()


def create_bid(
    client: TestClient,
    bidder: AuthenticatedUser,
    auction_id: int,
    *,
    amount: str | Decimal = "11.00",
) -> dict:
    response = client.post(
        f"/api/v1/bids/{auction_id}",
        headers=bidder.headers,
        json={"amount": str(amount)},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def test_user(client: TestClient, db_session: Session) -> AuthenticatedUser:
    return create_user(client, db_session, email="user@example.com")


@pytest.fixture
def test_seller(client: TestClient, db_session: Session) -> AuthenticatedUser:
    return create_user(client, db_session, email="seller@example.com", role=UserRole.SELLER)


@pytest.fixture
def test_admin(client: TestClient, db_session: Session) -> AuthenticatedUser:
    return create_user(client, db_session, email="admin@example.com", role=UserRole.ADMIN)
