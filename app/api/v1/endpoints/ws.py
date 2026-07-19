"""Auksion real-time WebSocket endpoint — narx/holat yangilanishlari kanali.

Mijoz `/api/v1/ws/auctions/{auction_id}?token=<JWT>` ga ulanadi va shu auksion
bo'yicha yangilanishlarni oladi. MVP'da endpoint oddiy RELAY: mijozdan kelgan
har qanday JSON xabar shu auksion room'idagi qolgan mijozlarga tarqatiladi.
Bu narx yangilanishini simulyatsiya qilish va testlash uchun yetarli.
Kelajakda broadcast'ni `bid_service` (bid qo'yilganda) ishga tushiradi.

Auth — ulanish uchun yaroqli access JWT MAJBURIY. Token `token` query
parametri orqali beriladi: WebSocket handshake'da maxsus sarlavha (Authorization)
qo'yish brauzer API'sida mumkin emas, shuning uchun query param — standart yechim.
Token yo'q yoki yaroqsiz (muddati o'tgan, imzosi noto'g'ri, tur access emas)
bo'lsa ulanish 4401 kod bilan yopiladi va `manager.connect` GA UMUMAN
o'tmaymiz (anonim ulanish room'ga qo'shilmaydi).
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.realtime.manager import manager

router = APIRouter()

# WebSocket auth muvaffaqiyatsizligi uchun close kodi. RFC 6455 application
# diapazoni (4000-4999) — 4401 "Unauthorized" HTTP 401 ga ohangdosh.
WS_UNAUTHORIZED_CODE = 4401


@router.websocket("/ws/auctions/{auction_id}")
async def auction_ws(
    websocket: WebSocket,
    auction_id: int,
    token: str | None = Query(default=None),
) -> None:
    """Auksion kanaliga ulanadi va mijoz xabarlarini shu kanalga relay qiladi.

    Ulanishdan oldin `token` query parametridagi access JWT tekshiriladi.
    Handshake'ni AVVAL qabul qilamiz (`accept`), keyin yaroqsiz tokenda
    close kod bilan yopamiz: aks holda close kodi (4401) mijozga yetib
    bormaydi — accept'dan oldingi close oddiy HTTP rad javobiga aylanadi.
    """
    await websocket.accept()

    payload = decode_access_token(token) if token else None
    if payload is None or payload.get("sub") is None:
        await websocket.close(code=WS_UNAUTHORIZED_CODE)
        return

    # user_id ni olamiz — kelajakda kim ulanganini kuzatish/bind qilish uchun.
    user_id = int(payload["sub"])  # noqa: F841 — MVP relay'da hali ishlatilmaydi

    manager.add(websocket, auction_id)
    try:
        while True:
            # MVP relay: mijozdan kelgan JSON'ni shu auksionni kuzatayotgan
            # qolgan barcha mijozlarga uzatamiz.
            message = await websocket.receive_json()
            await manager.broadcast(auction_id, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
