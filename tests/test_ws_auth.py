"""Auksion WebSocket JWT auth testlari.

WS endpoint endi ochiq emas: ulanish uchun `?token=<access JWT>` MAJBURIY.
Token yo'q yoki yaroqsiz bo'lsa server handshake'ni qabul qilgach 4401 kod
bilan yopadi — TestClient buni `WebSocketDisconnect` sifatida ko'taradi.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.api.v1.endpoints.ws import WS_UNAUTHORIZED_CODE
from tests.conftest import create_user


def test_connection_without_token_is_rejected(client: TestClient) -> None:
    """Token'siz ulanish rad etiladi — 4401 kod bilan yopiladi."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/auctions/1") as ws:
            # accept'dan keyin close bo'lgani uchun uzilish odatda birinchi
            # receive'da yuzaga chiqadi.
            ws.receive_json()

    assert exc_info.value.code == WS_UNAUTHORIZED_CODE


def test_connection_with_invalid_token_is_rejected(client: TestClient) -> None:
    """Yaroqsiz (soxta) token bilan ulanish rad etiladi."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/auctions/1?token=not-a-real-jwt") as ws:
            ws.receive_json()

    assert exc_info.value.code == WS_UNAUTHORIZED_CODE


def test_connection_with_valid_token_succeeds(client: TestClient, db_session: Session) -> None:
    """To'g'ri access token bilan ulanish muvaffaqiyatli — relay ishlaydi."""
    tok = create_user(client, db_session, email="wsauth@example.com").access_token

    with client.websocket_connect(f"/api/v1/ws/auctions/1?token={tok}") as ws:
        payload = {"type": "PING"}
        ws.send_json(payload)
        # broadcast room'dagi BARCHA ulanishlarga (jumladan yuboruvchiga)
        # yuboradi — echo qaytishi ulanish to'liq ochiq va relay ishlashini
        # tasdiqlaydi (4401 bilan yopilmagan).
        assert ws.receive_json() == payload
