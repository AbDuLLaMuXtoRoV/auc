"""normalize_search / translit va matnli qidiruv (ILIKE) testlari."""

from fastapi.testclient import TestClient

from app.services.translit import normalize_search, to_cyrillic, to_latin
from tests.conftest import AuthenticatedUser


def test_normalize_lowercases_and_trims() -> None:
    assert normalize_search("  Salom   Dunyo  ") == "salom dunyo"


def test_normalize_cyrillic_and_latin_converge() -> None:
    """Lotin va kirill bir xil kanonik satrga tushishi shart."""
    assert normalize_search("Kompyuter") == normalize_search("Компьютер")
    assert normalize_search("telefon") == normalize_search("телефон")


def test_normalize_strips_apostrophes_and_special_letters() -> None:
    # oʻ/gʻ -> o/g, apostroflar olib tashlanadi.
    assert normalize_search("Oʻzbekiston") == "ozbekiston"
    assert normalize_search("O'zbekiston") == "ozbekiston"
    assert normalize_search("gʻisht") == "gisht"


def test_normalize_cyrillic_o_and_g_special() -> None:
    # ў -> o, ғ -> g.
    assert normalize_search("ўзбек") == "ozbek"
    assert normalize_search("ғишт") == "gisht"


def test_to_latin_roundtrip_basic() -> None:
    assert to_latin("компьютер") == "kompyuter"
    assert to_latin("латин") == "latin"


def test_to_cyrillic_basic() -> None:
    # Taxminiy — asosiy tovushlar mos kelishi kifoya.
    assert to_cyrillic("salom") == "салом"


def test_search_endpoint_matches_across_scripts(
    client: TestClient,
    test_seller: AuthenticatedUser,
) -> None:
    """Kirill so'rov lotin e'lonni (va aksincha) topishi kerak."""
    create = client.post(
        "/api/v1/items",
        headers=test_seller.headers,
        json={
            "title": "Kompyuter Lenovo",
            "description": "Yaxshi holatda ishlaydi",
            "condition": "used",
            "defects": "kichik chizilgan joyi bor",
            "starting_price": "5000",
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    # Kirillcha yozib qidiramiz — lotincha e'lon topilishi shart.
    cyrillic = client.get("/api/v1/items", params={"q": "компьютер"})
    assert cyrillic.status_code == 200
    assert item_id in [entry["id"] for entry in cyrillic.json()]

    # Lotincha, katta harf, apostrof aralash — baribir topilishi kerak.
    latin = client.get("/api/v1/items", params={"q": "Kompyuter"})
    assert item_id in [entry["id"] for entry in latin.json()]

    # Mos kelmaydigan so'rov bo'sh natija berishi kerak.
    miss = client.get("/api/v1/items", params={"q": "muzlatgich"})
    assert item_id not in [entry["id"] for entry in miss.json()]
