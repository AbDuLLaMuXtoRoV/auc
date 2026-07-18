from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.auction_closer import start_auction_closer, stop_auction_closer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Ilova hayotiy sikli: closer worker'ni ishga tushiradi va to'xtatadi.

    Worker faqat yoqilgan va test bo'lmagan muhitda ishga tushadi
    (guard `start_auction_closer` ichida). Shutdown'da task bekor qilinadi.
    """
    closer_task = start_auction_closer()
    try:
        yield
    finally:
        await stop_auction_closer(closer_task)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")
    Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.public_upload_url_prefix,
        StaticFiles(directory=settings.local_upload_dir),
        name="uploads",
    )
    return app


app = create_app()
