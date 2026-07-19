from pydantic import BaseModel


class FraudSignals(BaseModel):
    """Admin uchun foydalanuvchi bo'yicha firibgarlik signallari (read-only).

    Barcha maydonlar agregat so'rovlardan kelib chiqadi — bironta ham
    xom PAN/token yoki maxfiy proxy summa oshkor bo'lmaydi. Signal ≠ hukm:
    bu faqat qo'lda tekshiruvni yo'naltiruvchi ko'rsatkichlar.
    """

    user_id: int
    # Shu foydalanuvchi bilan BIR device_id dan bid qo'ygan boshqa user_id'lar.
    shared_device_user_ids: list[int]
    # Shu foydalanuvchi bilan bir IP dan bid qo'ygan boshqa user_id'lar.
    shared_ip_user_ids: list[int]
    # Foydalanuvchi bid qo'ygan auksionlar ichida, o'sha auksion SOTUVCHISI
    # bilan bir IP/device ishlatilgan (shill halqasi) holatlar soni.
    self_auction_ip_overlap: int
    bid_count: int
    distinct_auctions: int
    # 10 soniyalik oynada eng ko'p bid soni (bot/velocity signali).
    rapid_bid_max_per_10s: int
    # Chegaralardan oshgan signallardan hosil bo'lgan matnli bayroqlar.
    risk_flags: list[str]
