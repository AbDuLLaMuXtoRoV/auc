from pathlib import Path

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.include_router(api_router, prefix="/api/v1")
    Path(settings.local_upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.public_upload_url_prefix,
        StaticFiles(directory=settings.local_upload_dir),
        name="uploads",
    )
    return app


app = create_app()
