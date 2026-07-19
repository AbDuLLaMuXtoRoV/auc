"""PSP webhook replay + dedup himoyasi uchun integratsiya testlari.

Endpoint imzoni XOM BAYT ustida tekshiradi, so'ng `WebhookService` orqali
replay (eski hodisa) va dedup (takroriy event_id) himoyasini qo'llaydi.
Testlar imzoni `compute_signature` bilan yasab yuboradi.
"""

import datetime
import json

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.webhook import compute_signature
from app.models.webhook_event import WebhookEvent

_URL = "/api/v1/payments/webhooks/psp"


def _now_ts() -> int:
    return int(datetime.datetime.now(datetime.UTC).timestamp())


def _signed_post(client: TestClient, payload: dict, *, secret: str | None = None) -> httpx.Response:
    raw = json.dumps(payload).encode()
    sig = compute_signature(raw, secret or settings.psp_webhook_secret)
    return client.post(_URL, content=raw, headers={"x-signature": sig})


def _event_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(WebhookEvent)) or 0


def test_webhook_missing_signature(client: TestClient) -> None:
    raw = json.dumps({"event_id": "e1", "timestamp": _now_ts(), "type": "capture"}).encode()
    r = client.post(_URL, content=raw)
    assert r.status_code == 401


def test_webhook_bad_signature(client: TestClient) -> None:
    raw = json.dumps({"event_id": "e1", "timestamp": _now_ts(), "type": "capture"}).encode()
    r = client.post(_URL, content=raw, headers={"x-signature": "deadbeef"})
    assert r.status_code == 401


def test_webhook_new_event_processed(client: TestClient, db_session: Session) -> None:
    r = _signed_post(client, {"event_id": "evt_1", "timestamp": _now_ts(), "type": "capture"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert _event_count(db_session) == 1

    event = db_session.scalar(select(WebhookEvent).where(WebhookEvent.event_id == "evt_1"))
    assert event is not None
    assert event.provider == "psp"
    assert event.processed_at is not None


def test_webhook_duplicate_event_deduped(client: TestClient, db_session: Session) -> None:
    payload = {"event_id": "evt_dup", "timestamp": _now_ts(), "type": "capture"}

    first = _signed_post(client, payload)
    assert first.status_code == 200
    assert _event_count(db_session) == 1

    # Aynan o'sha event_id ikkinchi marta (to'g'ri imzo) — DB'da hali BITTA.
    second = _signed_post(client, payload)
    assert second.status_code == 200
    assert second.json() == {"ok": True}
    assert _event_count(db_session) == 1


def test_webhook_stale_event_rejected(client: TestClient, db_session: Session) -> None:
    payload = {"event_id": "evt_old", "timestamp": _now_ts() - 1000, "type": "capture"}
    r = _signed_post(client, payload)
    assert r.status_code == 400
    # Stale hodisa yozilmaydi.
    assert _event_count(db_session) == 0


def test_webhook_missing_fields_rejected(client: TestClient) -> None:
    # event_id/timestamp/type bo'lmasa — 400.
    r = _signed_post(client, {"type": "capture"})
    assert r.status_code == 400
