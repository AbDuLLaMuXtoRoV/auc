"""Hudud/tuman public endpointlari: GET /regions, GET /regions/{id}/districts.

Seed skripti test'da ishlamaydi — ma'lumot to'g'ridan-to'g'ri db_session
orqali kiritiladi."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.region import District, Region


def _seed(db: Session) -> Region:
    region = Region(code="TAS_CITY", name_uz="Toshkent shahri", name_ru="город Ташкент")
    other = Region(code="AND", name_uz="Andijon viloyati", name_ru="Андижанская область")
    db.add_all([region, other])
    db.flush()
    db.add(District(region_id=region.id, name_uz="Chilonzor", name_ru="Чиланзар"))
    db.add(District(region_id=region.id, name_uz="Yunusobod", name_ru="Юнусабад"))
    db.commit()
    return region


def test_list_regions(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    resp = client.get("/api/v1/regions")
    assert resp.status_code == 200
    codes = {r["code"] for r in resp.json()}
    assert {"TAS_CITY", "AND"} <= codes


def test_regions_public_no_auth(client: TestClient, db_session: Session) -> None:
    _seed(db_session)
    # Authorization sarlavhasiz ham ochiq.
    resp = client.get("/api/v1/regions")
    assert resp.status_code == 200


def test_list_districts(client: TestClient, db_session: Session) -> None:
    region = _seed(db_session)
    resp = client.get(f"/api/v1/regions/{region.id}/districts")
    assert resp.status_code == 200
    names = {d["name_uz"] for d in resp.json()}
    assert names == {"Chilonzor", "Yunusobod"}


def test_districts_missing_region_404(client: TestClient, db_session: Session) -> None:
    resp = client.get("/api/v1/regions/99999/districts")
    assert resp.status_code == 404
