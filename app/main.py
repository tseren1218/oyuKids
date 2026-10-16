from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import pages, poems, reading, words
from app.web import BASE_DIR


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    for module in (pages, reading, words, poems):
        app.include_router(module.router)
    return app


app = create_app()
