"""Telefon narx ko'rsatkichi: won -> so'm, baho qoidalari, admin kursi, e'lon maydonlari."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.price_guide import DeviceModel, DevicePrice, PriceGuideSettings
from app.money import convert_foreign_to_tiyin
from tests.conftest import create_user

# 1 won = 10 so'm = 1000 tiyin — hisobni qo'lda tekshirish oson bo'lsin.
RATE = 1000


@pytest.fixture
def phone(db_session: Session) -> DeviceModel:
    db_session.add(PriceGuideSettings(id=1, rate_tiyin_per_krw=RATE, market_adjust_bps=0))
    model = DeviceModel(
        brand="Apple",
        name="iPhone 13",
        slug="iphone-13",
        series="13",
        sort_order=0,
        screen_broken_krw=10_000,
        lcd_krw=90_000,
        face_id_krw=55_000,
        camera_krw=50_000,
        back_glass_krw=0,
        scrap_krw=35_000,
    )
    model.prices = [
        DevicePrice(
            storage="128GB",
            sort_order=0,
            grade_a_krw=350_000,
            grade_a_minus_krw=330_000,
            grade_b_plus_krw=310_000,
            grade_b_minus_krw=None,  # jadvalda "X" — bu darajada sotib olinmaydi
            battery_low_a_krw=300_000,
            battery_low_b_plus_krw=None,
            base_krw=270_000,
        )
    ]
    db_session.add(model)
    db_session.commit()
    return model


def _estimate(client: TestClient, model_id: int, **kw) -> dict:
    body = {"model_id": model_id, "storage": "128GB", **kw}
    response = client.post("/api/v1/price-guide/estimate", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _soum(amount: int) -> str:
    """So'm -> tiyin satri (API formati)."""
    return str(amount * 100)


# --- Pul o'girish -----------------------------------------------------------


def test_convert_foreign_rounds_down_to_thousand_soum() -> None:
    # 123 456 won * 8.55 so'm = 1 055 548.8 so'm -> 1 055 000 so'm (pastga).
    assert convert_foreign_to_tiyin(123_456, 855) == 105_500_000
    # +15% bozor tuzatmasi.
    assert convert_foreign_to_tiyin(100_000, 1000, 1500) == 115_000_000
    assert convert_foreign_to_tiyin(0, 855) == 0


def test_convert_foreign_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        convert_foreign_to_tiyin(-1, 855)
    with pytest.raises(ValueError):
        convert_foreign_to_tiyin(100, 855, -10_000)


# --- Baho qoidalari ---------------------------------------------------------


def test_estimate_grade_price(client: TestClient, phone: DeviceModel) -> None:
    body = _estimate(client, phone.id, grade="a", battery_health=95)
    assert body["grade_price"] == _soum(3_500_000)
    assert body["estimate"] == _soum(3_500_000)
    assert body["battery_adjusted"] is False
    assert body["deductions"] == []


def test_low_battery_uses_battery_column(client: TestClient, phone: DeviceModel) -> None:
    body = _estimate(client, phone.id, grade="a", battery_health=85)
    assert body["estimate"] == _soum(3_000_000)
    assert body["battery_adjusted"] is True


def test_low_battery_without_column_drops_one_grade(client: TestClient, phone: DeviceModel) -> None:
    # B+ < 85%: "batareya past" narxi yo'q, B- esa "X" -> base.
    body = _estimate(client, phone.id, grade="b_plus", battery_health=80)
    assert body["estimate"] == _soum(2_700_000)
    assert body["battery_adjusted"] is True


def test_grade_not_bought_falls_back_to_base(client: TestClient, phone: DeviceModel) -> None:
    assert _estimate(client, phone.id, grade="b_minus")["estimate"] == _soum(2_700_000)
    assert _estimate(client, phone.id)["estimate"] == _soum(2_700_000)


def test_defects_are_deducted_once(client: TestClient, phone: DeviceModel) -> None:
    body = _estimate(client, phone.id, grade="a", defects=["lcd", "camera", "lcd", "back_glass"])
    # 350 000 - 90 000 - 50 000 = 210 000 won; back_glass = 0 -> ro'yxatda yo'q.
    assert body["estimate"] == _soum(2_100_000)
    assert [d["defect"] for d in body["deductions"]] == ["lcd", "camera"]


def test_estimate_never_below_scrap(
    client: TestClient, db_session: Session, phone: DeviceModel
) -> None:
    phone.scrap_krw = 100_000
    db_session.commit()
    body = _estimate(
        client, phone.id, grade="b_minus", defects=["lcd", "face_id", "camera", "screen_broken"]
    )
    # 270 000 - 205 000 = 65 000 won < "ehtiyot qism" narxi 100 000 won.
    assert body["estimate"] == _soum(1_000_000)
    assert body["floored_to_scrap"] is True


def test_estimate_unknown_storage_or_model(client: TestClient, phone: DeviceModel) -> None:
    bad_storage = {"model_id": phone.id, "storage": "1TB"}
    assert client.post("/api/v1/price-guide/estimate", json=bad_storage).status_code == 404
    bad_model = {"model_id": 9999, "storage": "128GB"}
    assert client.post("/api/v1/price-guide/estimate", json=bad_model).status_code == 404


def test_index_and_model_detail(client: TestClient, phone: DeviceModel) -> None:
    index = client.get("/api/v1/price-guide").json()
    assert index["info"]["rate_tiyin_per_krw"] == RATE
    assert index["models"] == [
        {
            "id": phone.id,
            "slug": "iphone-13",
            "brand": "Apple",
            "name": "iPhone 13",
            "series": "13",
            "storages": ["128GB"],
        }
    ]
    detail = client.get("/api/v1/price-guide/models/iphone-13").json()
    assert detail["prices"][0]["a"] == _soum(3_500_000)
    assert detail["prices"][0]["b_minus"] is None
    assert detail["deductions"]["lcd"] == _soum(900_000)
    assert "back_glass" not in detail["deductions"]  # 0 — ajratma yo'q
    assert client.get("/api/v1/price-guide/models/nope").status_code == 404


# --- Admin kursi --------------------------------------------------------------


def test_only_admin_can_change_rate(
    client: TestClient, db_session: Session, phone: DeviceModel
) -> None:
    user = create_user(client, db_session, email="user@example.com")
    admin = create_user(client, db_session, email="admin@example.com", role=UserRole.ADMIN)
    body = {"rate_tiyin_per_krw": 2000, "market_adjust_bps": 1000}
    url = "/api/v1/admin/price-guide/settings"

    assert client.put(url, headers=user.headers, json=body).status_code == 403
    response = client.put(url, headers=admin.headers, json=body)
    assert response.status_code == 200
    assert response.json()["rate_tiyin_per_krw"] == 2000

    # 350 000 won * 20 so'm * 1.10 = 7 700 000 so'm — darhol qayta hisoblanadi.
    assert _estimate(client, phone.id, grade="a")["estimate"] == _soum(7_700_000)


def test_rate_validation(client: TestClient, db_session: Session) -> None:
    admin = create_user(client, db_session, email="admin@example.com", role=UserRole.ADMIN)
    url = "/api/v1/admin/price-guide/settings"
    for bad in (
        {"rate_tiyin_per_krw": 0, "market_adjust_bps": 0},
        {"rate_tiyin_per_krw": 855, "market_adjust_bps": -9000},
    ):
        assert client.put(url, headers=admin.headers, json=bad).status_code == 422


def test_default_rate_when_not_configured(client: TestClient, db_session: Session) -> None:
    info = client.get("/api/v1/price-guide").json()["info"]
    assert info["rate_tiyin_per_krw"] == 855
    assert info["updated_at"] is None


# --- E'londagi telefon maydonlari ------------------------------------------


def _item(client: TestClient, seller, **device) -> dict:
    payload = {"title": "iPhone 13", "condition": "used", "starting_price": "100000", **device}
    return client.post("/api/v1/items", headers=seller.headers, json=payload)


def test_item_with_device_fields(
    client: TestClient, db_session: Session, phone: DeviceModel
) -> None:
    seller = create_user(client, db_session, email="seller@example.com")
    response = _item(
        client,
        seller,
        device_model_id=phone.id,
        device_storage="128GB",
        device_grade="a_minus",
        battery_health=91,
        device_defects=["camera", "camera"],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["device_model"] == {"id": phone.id, "slug": "iphone-13", "name": "iPhone 13"}
    assert body["device_grade"] == "a_minus"
    assert body["battery_health"] == 91
    assert body["device_defects"] == ["camera"]


def test_item_device_validation(
    client: TestClient, db_session: Session, phone: DeviceModel
) -> None:
    seller = create_user(client, db_session, email="seller@example.com")
    assert _item(client, seller, device_model_id=phone.id, device_storage="2TB").status_code == 400
    assert _item(client, seller, device_storage="128GB").status_code == 400
    assert _item(client, seller, device_model_id=9999).status_code == 400
    assert _item(client, seller, battery_health=120).status_code == 422
    assert _item(client, seller, device_grade="s_plus").status_code == 422
    # Telefon maydonlarisiz oddiy e'lon o'zgarishsiz ishlaydi.
    plain = _item(client, seller)
    assert plain.status_code == 201
    assert plain.json()["device_model"] is None
    assert plain.json()["device_defects"] == []


def test_item_update_device_fields(
    client: TestClient, db_session: Session, phone: DeviceModel
) -> None:
    seller = create_user(client, db_session, email="seller@example.com")
    item = _item(client, seller, device_model_id=phone.id, device_storage="128GB").json()
    url = f"/api/v1/items/{item['id']}"

    ok = client.patch(url, headers=seller.headers, json={"device_grade": "b_plus"})
    assert ok.status_code == 200
    assert ok.json()["device_grade"] == "b_plus"
    bad = client.patch(url, headers=seller.headers, json={"device_storage": "64GB"})
    assert bad.status_code == 400
