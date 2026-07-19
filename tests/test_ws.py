"""Auksion WebSocket relay + kanal izolyatsiyasi testlari.

DB kerak emas — WS endpoint faqat in-memory `ConnectionManager` bilan ishlaydi.
Biroq `client` fixture conftest orqali keladi (real Postgres'ga ulanadi):
zarari yo'q, WS handshake DB'ga tegmaydi.

DIQQAT: broadcast APP EVENT LOOP ichida sodir bo'ladi (mijoz xabar yuboradi →
endpoint `manager.broadcast` chaqiradi). Shu sabab testda `manager.broadcast`
TO'G'RIDAN-TO'G'RI chaqirilmaydi (u boshqa loop'da bo'lardi) — hamma narsa
endpoint relay orqali sinaladi.
"""

from fastapi.testclient import TestClient


def test_broadcast_reaches_other_client_in_same_room(client: TestClient) -> None:
    """Bir mijoz yuborgan xabar shu auksion kanalidagi boshqa mijozga yetadi."""
    with (
        client.websocket_connect("/api/v1/ws/auctions/1") as ws1,
        client.websocket_connect("/api/v1/ws/auctions/1") as ws2,
    ):
        payload = {"type": "BID_PLACED", "price": "1000"}
        ws1.send_json(payload)

        assert ws2.receive_json() == payload


def test_channels_are_isolated_across_auctions(client: TestClient) -> None:
    """Boshqa auksion kanalidagi mijoz begona xabarni OLMAYDI (izolyatsiya).

    ws3 auksion 2 da. Avval auksion 1 ga xabar yuboriladi (ws2 oladi), so'ng
    auksion 2 ga boshqa xabar yuboriladi. ws3 ning BIRINCHI olgan xabari
    aynan auksion-2 xabari bo'lishi kerak — agar auksion-1 xabari oqib
    o'tganida, FIFO navbatda u birinchi kelardi.
    """
    with (
        client.websocket_connect("/api/v1/ws/auctions/1") as ws1,
        client.websocket_connect("/api/v1/ws/auctions/1") as ws2,
        client.websocket_connect("/api/v1/ws/auctions/2") as ws3,
    ):
        auction1_msg = {"type": "BID_PLACED", "auction": 1, "price": "1000"}
        auction2_msg = {"type": "BID_PLACED", "auction": 2, "price": "5000"}

        # Auksion 1 kanaliga: faqat ws2 (va ws1) olishi kerak.
        ws1.send_json(auction1_msg)
        assert ws2.receive_json() == auction1_msg

        # Auksion 2 kanaliga: ws3 shuni oladi. Agar auksion-1 xabari ws3 ga
        # oqib o'tganida, bu birinchi qaytadigan xabar auction1_msg bo'lardi.
        ws3.send_json(auction2_msg)
        assert ws3.receive_json() == auction2_msg
