from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.deps import DEMO_KID_ID, get_repo
from app.navigation import ACTIVITIES, MORE, NAV

BASE_DIR = Path(__file__).resolve().parent


def _layout_context(request: Request) -> dict:
    repo = get_repo()
    return {
        "kid": repo.get_kid(DEMO_KID_ID),
        "stats": repo.kid_stats(DEMO_KID_ID),
        "nav": NAV,
        "more": MORE,
        "path": request.url.path,
    }


templates = Jinja2Templates(directory=BASE_DIR / "templates", context_processors=[_layout_context])
templates.env.globals["activities"] = ACTIVITIES
templates.env.filters["mmss"] = lambda s: f"{int(s) // 60:02d}:{int(s) % 60:02d}"
templates.env.filters["pct"] = lambda v: f"{round((v or 0) * 100)}%"
templates.env.filters["shortdate"] = lambda d: d.strftime("%m/%d · %H:%M")


def render(request: Request, name: str, **context):
    return templates.TemplateResponse(request, name, context)


def wants_fragment(request: Request, target: str) -> bool:
    """True for an htmx request aimed at `target` (as opposed to a boosted full-page load)."""
    return request.headers.get("HX-Target") == target


def or_404(item, what: str = "Олдсонгүй"):
    if item is None:
        raise HTTPException(status_code=404, detail=what)
    return item
