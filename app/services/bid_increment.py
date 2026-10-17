"""Dinamik minimal qadam jadvali.

Muammo: bitta qat'iy minimal qadam past narxda juda sekin (5 000 so'mlik
lotga 1 000 so'mlik qadamlar), yuqori narxda esa kulgili (10 000 000 so'mlik
lotga 1 000 so'mlik qadam — auksion cho'zilib ketadi). Yechim: joriy narxga
qarab qadamni oshiruvchi darajali jadval (eBay/Yahoo Auctions uslubi).

Barcha qiymatlar TIYINDA (so'm ×100). Jadval (so'mda -> tiyinda):
    < 100 000        -> 5 000     (< 10 000 000 tiyin   -> 500 000 tiyin)
    100 000..500 000 -> 10 000    (10 000 000..50 000 000 -> 1 000 000)
    500 000..2 000 000 -> 25 000  (50 000 000..200 000 000 -> 2 500 000)
    2 000 000..10 000 000 -> 100 000 (200 000 000..1 000 000 000 -> 10 000 000)
    > 10 000 000     -> 250 000   (> 1 000 000 000 tiyin -> 25 000 000)

Sotuvchi belgilagan `minimum_bid_increment` bu jadval bilan RAQOBATLASHMAYDI —
amaldagi qadam = max(sotuvchi qadami, jadval qadami). Ya'ni sotuvchi faqat
YUQORIROQ qadam qo'ya oladi, pastroq emas (auksionni sekinlashtira olmaydi).
"""

from app.money import Tiyin

# (yuqori chegara EKSKLYUZIV tiyinda, shu darajadagi qadam tiyinda).
# Oxirgi daraja cheksiz — None chegara.
_INCREMENT_TIERS: tuple[tuple[int | None, int], ...] = (
    (10_000_000, 500_000),  # < 100 000 so'm -> 5 000 so'm
    (50_000_000, 1_000_000),  # 100 000..500 000 so'm -> 10 000 so'm
    (200_000_000, 2_500_000),  # 500 000..2 000 000 so'm -> 25 000 so'm
    (1_000_000_000, 10_000_000),  # 2 000 000..10 000 000 so'm -> 100 000 so'm
    (None, 25_000_000),  # > 10 000 000 so'm -> 250 000 so'm
)


def min_increment_for_price(current_price_tiyin: Tiyin) -> Tiyin:
    """Joriy narxga (tiyin) mos jadval minimal qadamini (tiyin) qaytaradi.

    Chegara EKSKLYUZIV: narx aynan chegaraga teng bo'lsa keyingi darajaga
    o'tadi (masalan 100 000 so'm -> 10 000 so'mlik qadam).
    """
    for upper_bound, increment in _INCREMENT_TIERS:
        if upper_bound is None or current_price_tiyin < upper_bound:
            return increment
    # _INCREMENT_TIERS oxirgi elementi None chegara — bu yerga yetilmaydi.
    return _INCREMENT_TIERS[-1][1]


def effective_min_increment(current_price_tiyin: Tiyin, seller_increment_tiyin: Tiyin) -> Tiyin:
    """Amaldagi minimal qadam = max(sotuvchi qadami, jadval qadami).

    Sotuvchi jadvaldan YUQORI qadam qo'yishi mumkin, past emas.
    """
    return max(seller_increment_tiyin, min_increment_for_price(current_price_tiyin))
