"""StorageService.save_upload validatsiyasi testlari.

Bu testlar DB'ga tegmaydi — UploadFile'ni to'g'ridan-to'g'ri yasab tekshiradi.
Fayllar tmp_path ga yoziladi (settings.local_upload_dir monkeypatch qilingan),
shu sabab user loyihasidagi haqiqiy uploads/ katalogi iflos bo'lmaydi.
"""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.services.storage_service import StorageService


def _make_upload(content: bytes, *, filename: str, content_type: str) -> UploadFile:
    """content_type ni headers orqali beradigan UploadFile yasaydi."""
    headers = Headers({"content-type": content_type})
    return UploadFile(file=BytesIO(content), filename=filename, headers=headers)


@pytest.fixture(autouse=True)
def _isolate_upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Har test o'z tmp katalogiga yozadi."""
    monkeypatch.setattr(settings, "local_upload_dir", str(tmp_path))


def test_allowed_png_saved(tmp_path: Path) -> None:
    upload = _make_upload(
        b"\x89PNG\r\n\x1a\n fake image bytes", filename="photo.png", content_type="image/png"
    )

    url = StorageService().save_upload(upload, folder="items")

    assert url.startswith(settings.public_upload_url_prefix.rstrip("/") + "/items/")
    saved_files = list((tmp_path / "items").iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].suffix == ".png"
    assert saved_files[0].read_bytes() == b"\x89PNG\r\n\x1a\n fake image bytes"


def test_svg_rejected(tmp_path: Path) -> None:
    upload = _make_upload(
        b"<svg onload=alert(1)></svg>", filename="x.svg", content_type="image/svg+xml"
    )

    with pytest.raises(HTTPException) as exc:
        StorageService().save_upload(upload, folder="items")

    assert exc.value.status_code in (400, 415)
    # Diskka hech narsa yozilmasligi kerak.
    assert not (tmp_path / "items").exists() or not list((tmp_path / "items").iterdir())


def test_html_content_type_rejected(tmp_path: Path) -> None:
    # text/html — stored XSS uchun eng xavfli tur.
    upload = _make_upload(
        b"<html><script>alert(1)</script></html>", filename="evil.png", content_type="text/html"
    )

    with pytest.raises(HTTPException) as exc:
        StorageService().save_upload(upload, folder="items")

    assert exc.value.status_code in (400, 415)


def test_disallowed_suffix_rejected(tmp_path: Path) -> None:
    # content_type rasm bo'lsa ham suffix .html — rad etiladi.
    upload = _make_upload(b"data", filename="evil.html", content_type="image/png")

    with pytest.raises(HTTPException) as exc:
        StorageService().save_upload(upload, folder="items")

    assert exc.value.status_code in (400, 415)


def test_oversized_file_rejected_and_no_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "upload_max_bytes", 1000)
    big = b"x" * 5000  # limitdan katta
    upload = _make_upload(big, filename="big.png", content_type="image/png")

    with pytest.raises(HTTPException) as exc:
        StorageService().save_upload(upload, folder="items")

    assert exc.value.status_code == 413
    # Yarim fayl qolmasligi kerak.
    items_dir = tmp_path / "items"
    assert not items_dir.exists() or not list(items_dir.iterdir())


def test_file_at_limit_saved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_max_bytes", 1000)
    exact = b"y" * 1000  # aynan limit — o'tishi kerak
    upload = _make_upload(exact, filename="ok.png", content_type="image/png")

    url = StorageService().save_upload(upload, folder="items")

    assert "/items/" in url
    saved_files = list((tmp_path / "items").iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == exact
