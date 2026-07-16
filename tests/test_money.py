"""Pul arifmetikasi testlari.

Pul modulida xato = to'g'ridan-to'g'ri pul yo'qotish. Shu sababli bu yerda
chegaraviy holatlar (yaxlitlash, float, manfiy, juda katta summa) alohida
tekshiriladi.
"""

from decimal import Decimal

import pytest

from app.money import (
    BUYER_PREMIUM_BPS,
    calc_buyer_premium,
    calc_seller_payout,
    calc_total,
    format_soum,
    soum_to_tiyin,
    tiyin_to_soum,
)


class TestSoumToTiyin:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (Decimal("0"), 0),
            (Decimal("1"), 100),
            (Decimal("62000.50"), 6_200_050),
            (Decimal("0.01"), 1),
            (100, 10_000),
            ("62000.50", 6_200_050),
        ],
    )
    def test_converts_correctly(self, value: Decimal | int | str, expected: int) -> None:
        assert soum_to_tiyin(value) == expected

    def test_float_is_rejected(self) -> None:
        """float bilan pul TAQIQ — aniqlik jimgina yo'qoladi."""
        with pytest.raises(TypeError, match="float"):
            soum_to_tiyin(62000.50)

    def test_sub_tiyin_precision_is_rejected(self) -> None:
        """Tiyindan mayda qiymat jimgina yaxlitlanmaydi — xato beradi."""
        with pytest.raises(ValueError, match="mayda"):
            soum_to_tiyin(Decimal("0.001"))

    def test_garbage_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            soum_to_tiyin("salom")


class TestTiyinToSoum:
    def test_converts_back(self) -> None:
        assert tiyin_to_soum(6_200_050) == Decimal("62000.50")

    def test_round_trip_is_lossless(self) -> None:
        original = Decimal("123456.78")
        assert tiyin_to_soum(soum_to_tiyin(original)) == original

    def test_negative_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="manfiy"):
            tiyin_to_soum(-1)

    def test_bool_is_not_money(self) -> None:
        """bool ham int — lekin pul emas."""
        with pytest.raises(TypeError):
            tiyin_to_soum(True)


class TestBuyerPremium:
    def test_eight_percent_of_100k_soum(self) -> None:
        """Hujjatdagi misol: 100 000 so'm -> 8 000 so'm premium, jami 108 000."""
        price = soum_to_tiyin(Decimal("100000"))
        assert calc_buyer_premium(price) == soum_to_tiyin(Decimal("8000"))
        assert calc_total(price) == soum_to_tiyin(Decimal("108000"))

    def test_default_bps_is_800(self) -> None:
        assert BUYER_PREMIUM_BPS == 800

    def test_rounds_down_not_up(self) -> None:
        """Yaxlitlash pastga — foydalanuvchi foydasiga.

        1 tiyin * 8% = 0.08 tiyin -> 0 tiyin. Tiyindan mayda pul yo'q.
        """
        assert calc_buyer_premium(1) == 0
        assert calc_total(1) == 1

    def test_premium_of_zero_is_zero(self) -> None:
        assert calc_buyer_premium(0) == 0

    def test_total_always_equals_price_plus_premium(self) -> None:
        """Invariant: jami = narx + premium. Har doim, chegarada ham."""
        for price in [0, 1, 7, 99, 12_345, 6_200_050, 10**15]:
            assert calc_total(price) == price + calc_buyer_premium(price)

    def test_negative_price_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="manfiy"):
            calc_buyer_premium(-100)

    def test_negative_bps_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            calc_buyer_premium(100, bps=-1)


class TestSellerPayout:
    def test_mvp_zero_fee(self) -> None:
        assert calc_seller_payout(6_200_050) == 6_200_050

    def test_with_fee(self) -> None:
        assert calc_seller_payout(100_000, seller_fee_bps=500) == 95_000


class TestLargeAmounts:
    def test_no_precision_loss_at_uzs_scale(self) -> None:
        """UZS summalari katta — Numeric(12,2) bunga tor edi (~10 mlrd so'm).

        Butun sonli tiyinda Python cheklovsiz — 1 trillion so'm ham aniq.
        """
        one_trillion_soum = soum_to_tiyin(Decimal("1000000000000"))
        assert one_trillion_soum == 100_000_000_000_000
        assert tiyin_to_soum(one_trillion_soum) == Decimal("1000000000000.00")

    def test_bigint_upper_bound_is_enough(self) -> None:
        """Postgres BIGINT chegarasi ~9.2 * 10^18 tiyin = ~92 kvadrillion so'm."""
        bigint_max = 2**63 - 1
        assert soum_to_tiyin(Decimal("92000000000000000")) < bigint_max


class TestFormatSoum:
    @pytest.mark.parametrize(
        ("tiyin", "expected"),
        [
            (6_200_050, "62 000.50"),
            (100, "1.00"),
            (0, "0.00"),
            (100_000_000, "1 000 000.00"),
        ],
    )
    def test_formats_for_display(self, tiyin: int, expected: str) -> None:
        assert format_soum(tiyin) == expected
