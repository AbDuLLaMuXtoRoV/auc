"""Auksion real-time WebSocket endpoint — narx/holat yangilanishlari kanali.

Mijoz `/api/v1/ws/auctions/{auction_id}` ga ulanadi va shu auksion bo'yicha
yangilanishlarni oladi. MVP'da endpoint oddiy RELAY: mijozdan kelgan har
qanday JSON xabar shu auksion room'idagi qolgan mijozlarga tarqatiladi.
Bu narx yangilanishini simulyatsiya qilish va testlash uchun yetarli.
Kelajakda broadcast'ni `bid_service` (bid qo'yilganda) ishga tushiradi.

Auth — MVP'da WS ochiq (hech qanday token talab qilinmaydi).
TODO(realtime): query yoki subprotocol orqali JWT tokenni tekshirish
(anonim ulanishlar faqat READ, bid emas — baribir bid REST orqali ketadi).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.manager import manager

router = APIRouter()


@router.websocket("/ws/auctions/{auction_id}")
async def auction_ws(websocket: WebSocket, auction_id: int) -> None:
    """Auksion kanaliga ulanadi va mijoz xabarlarini shu kanalga relay qiladi."""
    await manager.connect(websocket, auction_id)
    try:
        while True:
            # MVP relay: mijozdan kelgan JSON'ni shu auksionni kuzatayotgan
            # qolgan barcha mijozlarga uzatamiz.
            message = await websocket.receive_json()
            await manager.broadcast(auction_id, message)
    except WebSocketDisconnect:
        manager.disconnect(websocket, auction_id)
