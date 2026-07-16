"""Tiyin arifmetikasi — pul bilan bog'liq yagona hisob-kitob joyi."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

# Pul turi. Bu shunchaki int alias'i — lekin tipda niyatni ko'rsatadi:
# "bu qiymat tiyinda, so'mda emas".
Tiyin = int

TIYIN_PER_SOUM = 100

# Buyer premium — xaridor to'laydigan komissiya. BPS = basis points.
# 800 BPS = 8%. Konfiguratsiyaga chiqarilishi mumkin, lekin default shu.
BUYER_PREMIUM_BPS = 800

_BPS_DIVISOR = 10_000


def soum_to_tiyin(value: Decimal | int | str) -> Tiyin:
    """So'mni tiyinga o'giradi: 62_000.50 -> 6_200_050.

    float QABUL QILINMAYDI — float'da 62_000.50 aniq ifodalanmaydi va
    jimgina bir tiyin yo'qolishi mumkin. Decimal, int yoki string bering.

    :raises TypeError: float berilsa.
    :raises ValueError: qiymat noto'g'ri yoki tiyindan mayda bo'lsa.
    """
    if isinstance(value, float):
        raise TypeError("float bilan pul TAQIQ — aniqlik yo'qoladi. Decimal, int yoki str bering.")

    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Pul qiymati noto'g'ri: {value!r}") from exc

    tiyin = amount * TIYIN_PER_SOUM
    if tiyin != tiyin.to_integral_value():
        raise ValueError(
            f"{value!r} tiyindan mayda — pul birligi tiyin, undan kichigi mavjud emas."
        )
    return int(tiyin)


def tiyin_to_soum(value: Tiyin) -> Decimal:
    """Tiyinni so'mga o'giradi (ko'rsatish uchun): 6_200_050 -> Decimal('62000.50').

    Faqat KO'RSATISH uchun. Hisob-kitob tiyinda qilinadi.
    """
    _assert_tiyin(value)
    return (Decimal(value) / TIYIN_PER_SOUM).quantize(Decimal("0.01"))


def format_soum(value: Tiyin) -> str:
    """Foydalanuvchiga ko'rsatish uchun matn: 6_200_050 -> '62 000.50'."""
    soum = tiyin_to_soum(value)
    whole, _, fraction = f"{soum:.2f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", " ")
    return f"{grouped}.{fraction}"


def calc_buyer_premium(price: Tiyin, bps: int = BUYER_PREMIUM_BPS) -> Tiyin:
    """Xaridor komissiyasi. Yaxlitlash FAQAT shu yerda bo'ladi.

    Butun sonli bo'lish ishlatiladi (pastga yaxlitlash) — foydalanuvchi
    foydasiga. Yaxlitlash boshqa joyda takrorlansa, jami summa qismlar
    yig'indisiga teng bo'lmay qoladi.
    """
    _assert_tiyin(price)
    if bps < 0:
        raise ValueError(f"BPS manfiy bo'lishi mumkin emas: {bps}")
    return price * bps // _BPS_DIVISOR


def calc_total(price: Tiyin, bps: int = BUYER_PREMIUM_BPS) -> Tiyin:
    """Xaridor to'laydigan umumiy summa = narx + premium."""
    return price + calc_buyer_premium(price, bps)


def calc_seller_payout(price: Tiyin, seller_fee_bps: int = 0) -> Tiyin:
    """Sotuvchi oladigan summa. MVP: sotuvchi komissiyasi 0%."""
    _assert_tiyin(price)
    if seller_fee_bps < 0:
        raise ValueError(f"BPS manfiy bo'lishi mumkin emas: {seller_fee_bps}")
    return price - (price * seller_fee_bps // _BPS_DIVISOR)


def _assert_tiyin(value: Tiyin) -> None:
    """Tiyin butun va manfiy emasligini tekshiradi.

    bool ham int — lekin pul emas, shuning uchun alohida rad etiladi.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Tiyin butun son bo'lishi kerak, berildi: {type(value).__name__}")
    if value < 0:
        raise ValueError(f"Pul manfiy bo'lishi mumkin emas: {value}")


def quantize_soum(value: Decimal) -> Decimal:
    """Decimal so'mni tiyingacha yaxlitlaydi (eski ma'lumot ko'chirishda kerak)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
