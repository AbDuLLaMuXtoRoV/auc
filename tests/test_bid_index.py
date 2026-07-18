"""Regressiya qalqoni: bids jadvalidagi kompozit index mavjudligini tekshiradi.

`get_highest_valid_bid` auksion bo'yicha eng yuqori `amount` ni (teng bo'lsa eng
erta `created_at`) qidiradi. Bu so'rov tez bo'lishi uchun modelda
`ix_bids_auction_amount_created (auction_id, amount, created_at)` kompozit index
e'lon qilingan (`app/models/bid.py`). Agar kimdir uni o'chirib yuborsa yoki
ustunlar tartibini buzsa — so'rov jimgina sekinlashadi, hech qanday test
yiqilmaydi. Shu test aynan o'sha regressiyani tutadi.

`db_engine` fixture sxemani `create_all` bilan model indekslari bilan quradi,
shuning uchun indeks metama'lumotini to'g'ridan-to'g'ri Postgres'dan o'qiymiz.
"""

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

INDEX_NAME = "ix_bids_auction_amount_created"
EXPECTED_COLUMNS = ["auction_id", "amount", "created_at"]


def test_bids_composite_index_exists(db_engine: Engine) -> None:
    indexes = inspect(db_engine).get_indexes("bids")
    by_name = {index["name"]: index for index in indexes}

    assert INDEX_NAME in by_name, (
        f"'{INDEX_NAME}' kompozit indeksi yo'q — g'olib bidni topish so'rovi "
        f"sekinlashadi. Mavjud indekslar: {sorted(by_name)}"
    )

    # Ustunlar tartibi muhim: (auction_id, amount, created_at) — filtr + saralash
    # shu tartibda ishlaydi. Tartib buzilsa index samarasiz bo'ladi.
    assert by_name[INDEX_NAME]["column_names"] == EXPECTED_COLUMNS
