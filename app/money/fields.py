"""Pul uchun Pydantic turi — API chegarasidagi yagona shartnoma.

Qoida: pul JSON'da HAR DOIM string, qiymat TIYINDA.
    {"amount": "6200050"}   = 62 000.50 so'm

Nega string, number emas? JavaScript'da `number` — IEEE-754 double.
2^53 dan katta butun son jimgina buziladi. Hozirgi summalar bunga
yetmaydi, lekin pul shartnomasini "hozircha yetadi" ustiga qurish
xavfli: bir kun yetmay qolganda xato jimgina va tiklab bo'lmaydigan
bo'ladi. String'da bu muammo umuman tug'ilmaydi.

Nega tiyin, so'm emas? So'mda kasr qismi paydo bo'ladi -> mijoz uni
float'ga o'girib jimgina aniqlik yo'qotadi. Butun sonda bunday yo'l yo'q.
"""

from typing import Annotated, Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema

from app.money.money import Tiyin


def _validate_tiyin(value: Any) -> int:
    """int yoki raqamli string qabul qiladi, tiyin (int) qaytaradi.

    float ATAYLAB rad etiladi — pul float orqali o'tsa aniqlik yo'qoladi.
    bool ham rad etiladi (bool int'ning bo'lasi, lekin pul emas).
    """
    if isinstance(value, bool):
        raise ValueError("Pul qiymati bool bo'lishi mumkin emas")
    if isinstance(value, float):
        raise ValueError(
            "Pul float sifatida yuborilmaydi — aniqlik yo'qoladi. "
            'Tiyinni string sifatida bering: "6200050"'
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("Pul qiymati bo'sh")
        try:
            return int(text)
        except ValueError as exc:
            raise ValueError(
                f"Pul tiyinda butun son bo'lishi kerak, berildi: {value!r}. "
                'Masalan 62 000.50 so\'m -> "6200050"'
            ) from exc
    raise ValueError(f"Pul qiymati noto'g'ri turda: {type(value).__name__}")


class _TiyinPydanticAnnotation:
    """int'ni saqlaydi, JSON'ga string sifatida yozadi.

    `before` validator + int sxemasi ishlatiladi (plain validator EMAS):
    plain validator sxemani "qora quti" qilib qo'yadi va sxemadagi
    Field(gt=0) kabi cheklovlar JIMGINA e'tiborsiz qoladi — ya'ni manfiy
    narx o'tib ketadi. `handler(int)` esa haqiqiy int sxemasini qaytaradi,
    cheklovlar unga bog'lanadi.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_before_validator_function(
            _validate_tiyin,
            handler(int),
            serialization=core_schema.plain_serializer_function_ser_schema(
                str,
                return_schema=core_schema.str_schema(),
                when_used="json",
            ),
        )


# Pul maydoni: kiruvchi "6200050" yoki 6200050 -> int; chiquvchi JSON -> "6200050".
# Musbatlik/chegara tekshiruvi sxemada Field(gt=0) bilan qo'shiladi.
TiyinAmount = Annotated[Tiyin, _TiyinPydanticAnnotation]
