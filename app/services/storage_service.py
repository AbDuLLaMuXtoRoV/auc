import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# Faqat rasm turlari ruxsat etiladi. SVG ATAYLAB yo'q: u ichida
# <script> tashib stored XSS beradi, HTML ham xuddi shunday. Bulardan
# tashqari har qanday turdagi fayl (masalan text/html) rad etiladi.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)
# Kengaytma ham cheklanadi: content_type qalbakilashtirilsa ham
# faylning suffixi ruxsat etilgan rasm formatlaridan biri bo'lishi shart.
ALLOWED_SUFFIXES: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})

# Faylni bir marta xotiraga to'liq yuklamay, oqim orqali bo'lak-bo'lak
# o'qiymiz — katta fayl bilan xotira DoS bo'lmasin.
_CHUNK_SIZE = 64 * 1024


class StorageService:
    """Local starter storage abstraction.

    TODO: Replace this implementation with S3, Cloudflare R2, or another object store
    without changing item service or endpoint code.
    """

    def save_upload(self, file: UploadFile, *, folder: str) -> str:
        """Yuklangan faylni validatsiyadan o'tkazib lokal diskka saqlaydi.

        Saqlashdan OLDIN turi/kengaytmasi tekshiriladi (stored XSS himoyasi),
        yozish davomida hajm sanaladi (DoS himoyasi). Limit oshsa yarim
        yozilgan fayl o'chiriladi — diskda buzuq fayl qolmaydi.
        """
        content_type = (file.content_type or "").lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="Unsupported media type")

        original_suffix = Path(file.filename or "").suffix.lower()
        if original_suffix not in ALLOWED_SUFFIXES:
            raise HTTPException(status_code=415, detail="Unsupported media type")

        upload_dir = Path(settings.local_upload_dir) / folder
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4().hex}{original_suffix}"
        destination = upload_dir / filename

        max_bytes = settings.upload_max_bytes
        written = 0
        try:
            with destination.open("wb") as output:
                while True:
                    chunk = file.file.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_bytes:
                        raise HTTPException(status_code=413, detail="File too large")
                    output.write(chunk)
        except HTTPException:
            # Yarim yozilgan faylni o'chirib tashlaymiz.
            destination.unlink(missing_ok=True)
            raise

        # Metadata (jumladan GPS koordinatalari) tozalanadi — maxfiylik.
        self._strip_image_metadata(destination)

        public_prefix = settings.public_upload_url_prefix.rstrip("/")
        return f"{public_prefix}/{folder}/{filename}"

    def _strip_image_metadata(self, path: Path) -> None:
        """Rasmni qayta kodlab EXIF/GPS metama'lumotini olib tashlaydi.

        Nega: telefon suratlari ko'pincha GPS koordinatalarini EXIF'da olib
        yuradi — uni public rasmda qoldirish sotuvchi manzilini fosh qiladi.
        Pillow'ni qayta kodlashda JPEG/PNG/WEBP EXIF'ni default tashlab yuboradi.

        Graceful: Pillow yo'q (ImportError) yoki fayl rasm sifatida dekod
        bo'lmasa (masalan test soxta baytlari) — ogohlantirish yozib, xom
        faylni o'z holicha qoldiramiz. Ilova yiqilmasligi kerak.
        """
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow o'rnatilmagan — rasm EXIF tozalanmadi: %s", path.name)
            return

        try:
            with Image.open(path) as image:
                # Animatsion rasmlarni (GIF/WEBP) buzib qo'ymaslik uchun
                # qayta kodlamaymiz — ular odatda GPS EXIF olib yurmaydi.
                if getattr(image, "is_animated", False):
                    return
                image.load()
                image_format = image.format
                clean = image.copy()
            # Fayl deskriptori yopilgach yozamiz (Windows'da qayta yozish uchun).
            clean.save(path, format=image_format)
        except Exception as exc:  # noqa: BLE001 — har qanday dekod xatosida xom saqlaymiz
            logger.warning("Rasm EXIF tozalanmadi (%s): %s", path.name, exc)
