"""In-memory WebSocket connection manager — auksion kanallariga fan-out.

Har bir auksion o'z "room"iga ega: `auction_id -> ulangan WebSocketlar to'plami`.
Bir room'dagi biror WebSocket'ga yuborilgan xabar shu auksionni kuzatayotgan
BARCHA mijozlarga tarqatiladi (broadcast).

DIQQAT — bu SINGLE-instance (bitta jarayon xotirasida) yechim. Bir nechta
ilova instansiyasi (horizontal scale) bo'lganda, bir instansiyaga ulangan
mijoz boshqa instansiyada sodir bo'lgan bid'ni KO'RMAYDI. Ko'p instansiyada
fan-out uchun Redis pub/sub kerak (har instansiya broadcast'ni pub qiladi,
qolganlari sub qilib o'z room'lariga uzatadi).
TODO(realtime): Redis pub/sub fan-out qatlamini ulash.
"""

from fastapi import WebSocket


class ConnectionManager:
    """Auksion room'lari bo'yicha WebSocket ulanishlarini boshqaradi.

    Holat faqat xotirada — jarayon qayta ishga tushsa ulanishlar yo'qoladi
    (mijoz qayta ulanadi). Thread-safe emas, lekin asyncio bitta event
    loop'da ishlagani uchun (await nuqtalari orasida atomik) MVP uchun yetarli.
    """

    def __init__(self) -> None:
        # auction_id -> shu auksionni kuzatayotgan ochiq WebSocketlar to'plami.
        self._rooms: dict[int, set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, auction_id: int) -> None:
        """WebSocket handshake'ni qabul qiladi va uni auksion room'iga qo'shadi."""
        await ws.accept()
        self._rooms.setdefault(auction_id, set()).add(ws)

    def add(self, ws: WebSocket, auction_id: int) -> None:
        """Allaqachon `accept` qilingan WebSocket'ni auksion room'iga qo'shadi.

        `connect`'dan farqi: handshake'ni QABUL QILMAYDI. Endpoint tokenni
        tekshirish uchun `accept`'ni o'zi chaqirgan holatlarda ishlatiladi
        (accept ikki marta chaqirilsa xato bo'ladi).
        """
        self._rooms.setdefault(auction_id, set()).add(ws)

    def disconnect(self, ws: WebSocket, auction_id: int) -> None:
        """WebSocket'ni room'dan olib tashlaydi; room bo'shab qolsa uni tozalaydi.

        Idempotent — allaqachon olib tashlangan ulanish uchun xato bermaydi.
        """
        room = self._rooms.get(auction_id)
        if room is None:
            return
        room.discard(ws)
        if not room:
            del self._rooms[auction_id]

    async def broadcast(self, auction_id: int, message: dict) -> None:
        """Auksion room'idagi barcha ulangan WebSocketlarga `message` ni yuboradi.

        Uzilgan yoki xato beruvchi ulanishlar xavfsiz o'tkazib yuboriladi va
        room'dan tozalanadi — bitta "o'lik" ulanish qolganlarga xabar
        yetkazishni to'xtatmasligi kerak.
        """
        room = self._rooms.get(auction_id)
        if not room:
            return

        # Nusxa ustidan aylanamiz: yuborish paytida to'plamni o'zgartirsak
        # (uzilganlarni tozalasak) "set changed size during iteration" bo'lmasin.
        dead: list[WebSocket] = []
        for ws in list(room):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 — har qanday uzilishda ulanishni tashlaymiz
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, auction_id)


# Yagona modul-darajali instansiya — butun ilova shu obyektni ulashadi.
# (Bir jarayon = bitta manager. Ko'p jarayon uchun yuqoridagi Redis TODO.)
manager = ConnectionManager()
