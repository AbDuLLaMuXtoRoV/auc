"""Lotin/kirill translit va qidiruv normalizatsiyasi.

Nega kerak: O'zbekistonda foydalanuvchilar bir xil so'zni ham lotin
("kompyuter"), ham kirill ("компьютер") yozadi. Qidiruv ikkalasini ham
topishi shart. Yechim — indekslashda va so'rovda matnni YAGONA kanonik
lotin shakliga keltiramiz, so'ng ILIKE bilan solishtiramiz.

Kutubxonasiz, oddiy dict asosida. Maqsad — 100% tilshunoslik aniqligi
emas, balki qidiruvni ishlatuvchi darajadagi moslik.
"""

import re

# Kirill -> lotin. Ko'p harfli almashuvlar (ch, sh, yo...) oldin qo'yiladi.
# O'zbek + rus harflari birga: ў, қ, ғ, ҳ ham qamraladi.
_CYRILLIC_TO_LATIN: dict[str, str] = {
    "ё": "yo",
    "ж": "j",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ю": "yu",
    "я": "ya",
    "ў": "o",
    "қ": "q",
    "ғ": "g",
    "ҳ": "h",
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "ъ": "",
    "ы": "i",
    "ь": "",
    "э": "e",
}

# Lotin -> kirill (o'zbek). Ko'p harfli birikmalar oldin ko'riladi.
# Bu yordamchi funksiya; qidiruv normalizatsiyasi lotinni kanon deb oladi.
_LATIN_MULTI_TO_CYRILLIC: list[tuple[str, str]] = [
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ch", "ч"),
    ("sh", "ш"),
    ("ts", "ц"),
    ("oʻ", "ў"),
    ("gʻ", "ғ"),
]
_LATIN_SINGLE_TO_CYRILLIC: dict[str, str] = {
    "a": "а",
    "b": "б",
    "d": "д",
    "e": "е",
    "f": "ф",
    "g": "г",
    "h": "ҳ",
    "i": "и",
    "j": "ж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "қ",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "x": "х",
    "y": "й",
    "z": "з",
    "c": "с",
    "w": "в",
}

# Apostrof variantlari: ASCII ', teskari `, tutuq belgisi ʻ va oʼ, ' , ' .
_APOSTROPHES = "'`ʻʼ‘’´"
_APOSTROPHE_RE = re.compile(f"[{re.escape(_APOSTROPHES)}]")
_WHITESPACE_RE = re.compile(r"\s+")


def to_latin(text: str) -> str:
    """Kirill matnni lotinga o'giradi. Lotin harflar o'zgarmaydi."""
    result: list[str] = []
    for char in text:
        lower = char.lower()
        mapped = _CYRILLIC_TO_LATIN.get(lower)
        if mapped is None:
            result.append(char)
        else:
            result.append(mapped)
    return "".join(result)


def to_cyrillic(text: str) -> str:
    """Lotin matnni taxminiy o'zbek kirilliga o'giradi.

    Ko'p harfli birikmalar (sh, ch, yo...) oldin almashtiriladi, so'ng
    yakka harflar. Aniqlik taxminiy — qidiruv uchun yetarli.
    """
    lowered = text.lower()
    # o' / g' -> ў / ғ ni ushlash uchun apostrofni normallashtiramiz.
    lowered = _APOSTROPHE_RE.sub("ʻ", lowered)
    for latin, cyr in _LATIN_MULTI_TO_CYRILLIC:
        lowered = lowered.replace(latin, cyr)
    result: list[str] = []
    for char in lowered:
        result.append(_LATIN_SINGLE_TO_CYRILLIC.get(char, char))
    return "".join(result)


def normalize_search(text: str) -> str:
    """Matnni qidiruv uchun kanonik lotin shakliga keltiradi.

    Bosqichlar:
      1. kichik harf;
      2. oʻ/ў -> o, gʻ/ғ -> g (o'zbekcha maxsus tovushlar);
      3. kirill -> lotin;
      4. apostroflarni olib tashlash;
      5. ortiqcha bo'shliqlarni siqish.

    Natija: "Kompyuter" va "Компьютер" bir xil satrga tushadi, shu bois
    ILIKE bo'yicha bir-birini topadi.
    """
    lowered = text.lower()
    # Apostrofni bir ko'rinishga keltirib, o'/g' juftlarini soddalashtiramiz.
    lowered = _APOSTROPHE_RE.sub("ʻ", lowered)
    lowered = lowered.replace("oʻ", "o").replace("gʻ", "g")
    # Kirilldagi ў/ғ ham to'g'ridan-to'g'ri o/g ga o'tadi (mapping ичида).
    latinized = to_latin(lowered)
    # Qolgan apostroflarni butunlay olib tashlaymiz.
    without_apostrophes = _APOSTROPHE_RE.sub("", latinized)
    collapsed = _WHITESPACE_RE.sub(" ", without_apostrophes)
    return collapsed.strip()
