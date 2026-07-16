from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository


def _register_and_login(client: TestClient, email: str) -> str:
    password = "Password1"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def _create_category(db_session: Session) -> Category:
    category = Category(name="Tools", slug="tools", description="Tools")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


def test_item_crud_filters_permissions_and_upload(
    client: TestClient,
    db_session: Session,
) -> None:
    seller_token = _register_and_login(client, "seller@example.com")
    other_token = _register_and_login(client, "other@example.com")
    admin_token = _register_and_login(client, "admin@example.com")

    admin_user = UserRepository(db_session).get_by_email("admin@example.com")
    assert admin_user is not None
    UserRepository(db_session).set_role(admin_user, UserRole.ADMIN)

    category = _create_category(db_session)

    create_response = client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={
            "title": "Cordless drill",
            "description": "Bare tool only",
            "category_id": category.id,
            "condition": "used",
            "location": "Tashkent",
            "item_location": "Tashkent warehouse",
            "starting_price": "50.00",
        },
    )
    assert create_response.status_code == 201
    item = create_response.json()
    item_id = item["id"]
    seller_id = item["seller_id"]

    get_response = client.get(f"/api/v1/items/{item_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Cordless drill"

    category_filter_response = client.get(f"/api/v1/items?category_id={category.id}")
    assert category_filter_response.status_code == 200
    assert [entry["id"] for entry in category_filter_response.json()] == [item_id]

    seller_filter_response = client.get(f"/api/v1/items?seller_id={seller_id}")
    assert seller_filter_response.status_code == 200
    assert [entry["id"] for entry in seller_filter_response.json()] == [item_id]

    status_filter_response = client.get("/api/v1/items?status=draft")
    assert status_filter_response.status_code == 200
    assert [entry["id"] for entry in status_filter_response.json()] == [item_id]

    location_filter_response = client.get("/api/v1/items?location=warehouse")
    assert location_filter_response.status_code == 200
    assert [entry["id"] for entry in location_filter_response.json()] == [item_id]

    forbidden_update = client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"title": "Not allowed"},
    )
    assert forbidden_update.status_code == 403

    owner_update = client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {seller_token}"},
        json={"title": "Cordless drill kit"},
    )
    assert owner_update.status_code == 200
    assert owner_update.json()["title"] == "Cordless drill kit"

    admin_update = client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"description": "Admin-managed description"},
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["description"] == "Admin-managed description"

    upload_response = client.post(
        f"/api/v1/items/{item_id}/images",
        headers={"Authorization": f"Bearer {seller_token}"},
        files={"file": ("drill.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"is_primary": "true"},
    )
    assert upload_response.status_code == 201
    image = upload_response.json()["image"]
    assert image["item_id"] == item_id
    assert image["image_url"].startswith("/uploads/items/")
    assert image["is_primary"] is True

    cancel_response = client.delete(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"
