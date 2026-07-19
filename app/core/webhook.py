"""PSP webhook imzosini tekshiruvchi sof utillar.

NEGA muhim: imzosiz webhook = istalgan odam soxta "to'landi" hodisasini yuborib,
haqiqiy to'lovsiz tovarni bepul olib ketishi mumkin. Shu sabab har bir kiruvchi
webhook HMAC imzosi bilan tasdiqlanishi va replay hujumidan himoyalanishi shart.

Bu modul DB'ga ham, config'ga ham bog'lanmaydi — sof funksiyalar, oson test qilinadi.
"""

import hashlib
import hmac


def compute_signature(raw_body: bytes, secret: str) -> str:
    """HMAC-SHA256 imzoni hisoblab, hex-string qaytaradi.

    NEGA xom bayt (raw_body) ustida: JSON'ni parse qilib, keyin qayta serializatsiya
    qilsak, kalitlar tartibi/bo'shliqlar o'zgarib imzo mos kelmay qoladi. PSP imzoni
    aynan yuborgan baytlar ustida hisoblaydi — biz ham xuddi shu baytlarni ishlatamiz.
    """
    return hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()


def verify_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Kelgan imzo xom bayt ustidagi kutilgan imzoga mos kelishini tekshiradi.

    NEGA hmac.compare_digest: oddiy `==` solishtiruvi mos kelmagan birinchi baytda
    tez to'xtaydi — bu javob vaqti orqali imzoni belgi-belgi topib olishga (timing
    attack) imkon beradi. compare_digest esa doimiy vaqtda solishtiradi.

    Formati noto'g'ri (masalan hex bo'lmagan) imzo istisno tashlamaydi, False qaytaradi.
    """
    expected = compute_signature(raw_body, secret)
    return hmac.compare_digest(expected, signature)


def is_fresh(event_timestamp: int, now_ts: int, max_age_seconds: int = 300) -> bool:
    """Hodisa juda eski emasligini tekshiradi (replay himoyasi).

    NEGA replay himoyasi: imzo to'g'ri bo'lsa ham, hujumchi eski (lekin haqiqiy)
    webhook'ni qayta yuborsa, hodisa takroran qayta ishlanishi mumkin. Shuning uchun
    hodisa vaqti hozirgi vaqtdan `max_age_seconds` dan ortiq eski bo'lsa, rad etamiz.

    Vaqtlar unix epoch soniyada. Kelajakdagi timestamp ham qabul qilinadi (soat
    farqlariga bardosh); faqat haddan tashqari eskilar bloklanadi.
    """
    return now_ts - event_timestamp <= max_age_seconds
