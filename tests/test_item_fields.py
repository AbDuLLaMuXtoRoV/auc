"""Item domen boyitish maydonlari, reserve_price yashirilishi va rasm limiti."""

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import AuthenticatedUser


def _base_payload(**overrides: object) -> dict:
    payload: dict = {
        "title": "Samsung telefon",
        "description": "Ishlaydi",
        "condition": "used",
        "defects": "ekranda mayda chiziq",
        "starting_price": "5000",
    }
    payload.update(overrides)
    return payload


def test_create_persists_new_domain_fields(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    response = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json=_base_payload(
            year=2021,
            equipment="quti, zaryadchi",
            defects="nuqson yo'q",
            video_url="https://example.com/v.mp4",
        ),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["year"] == 2021
    assert body["equipment"] == "quti, zaryadchi"
    assert body["defects"] == "nuqson yo'q"
    assert body["video_url"] == "https://example.com/v.mp4"
    assert body["view_count"] == 0
    assert body["published_at"] is None


def test_defects_is_optional(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    # MVP'da defects ixtiyoriy — berilmasa ham e'lon yaratiladi (None saqlanadi).
    payload = _base_payload()
    del payload["defects"]
    response = client.post("/api/v1/items", headers=test_seller.headers, json=payload)
    assert response.status_code == 201
    assert response.json()["defects"] is None


def test_reserve_price_hidden_but_has_reserve_exposed(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    """reserve_price public javobda YO'Q; faqat has_reserve bo'ladi."""
    with_reserve = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json=_base_payload(reserve_price="9000"),
    )
    assert with_reserve.status_code == 201
    body = with_reserve.json()
    assert "reserve_price" not in body
    assert body["has_reserve"] is True

    without_reserve = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json=_base_payload(title="Boshqa telefon"),
    )
    body2 = without_reserve.json()
    assert "reserve_price" not in body2
    assert body2["has_reserve"] is False


def test_image_upload_limit_enforced(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    create = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json=_base_payload(),
    )
    item_id = create.json()["id"]

    limit = settings.max_images_per_item
    for index in range(limit):
        upload = client.post(
            f"/api/v1/items/{item_id}/images",
            headers=test_seller.headers,
            files={"file": (f"img{index}.jpg", b"fake-image-bytes", "image/jpeg")},
        )
        assert upload.status_code == 201

    # Limitdan oshgan navbatdagi yuklash rad etilishi kerak.
    overflow = client.post(
        f"/api/v1/items/{item_id}/images",
        headers=test_seller.headers,
        files={"file": ("extra.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert overflow.status_code == 400
