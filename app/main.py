import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.auth import LoginRequired, WrongRole, on_login_required, on_wrong_role
from app.config import get_settings
from app.routers import auth, classes, pages, poems, reading, teacher, words
from app.services.stt import STTError
from app.web import BASE_DIR

log = logging.getLogger("oyukids")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    for module in (auth, pages, classes, reading, words, poems, teacher):
        app.include_router(module.router)
    app.add_exception_handler(LoginRequired, on_login_required)
    app.add_exception_handler(WrongRole, on_wrong_role)

    @app.exception_handler(STTError)
    async def stt_failed(request: Request, exc: STTError):
        # recorder.js shows its retry message for any non-2xx response
        log.warning("STT failed: %s", exc)
        return HTMLResponse("STT unavailable", status_code=502)

    return app


app = create_app()
