from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    """Local starter storage abstraction.

    TODO: Replace this implementation with S3, Cloudflare R2, or another object store
    without changing item service or endpoint code.
    """

    def save_upload(self, file: UploadFile, *, folder: str) -> str:
        upload_dir = Path(settings.local_upload_dir) / folder
        upload_dir.mkdir(parents=True, exist_ok=True)

        original_suffix = Path(file.filename or "").suffix
        filename = f"{uuid4().hex}{original_suffix}"
        destination = upload_dir / filename

        with destination.open("wb") as output:
            copyfileobj(file.file, output)

        public_prefix = settings.public_upload_url_prefix.rstrip("/")
        return f"{public_prefix}/{folder}/{filename}"
