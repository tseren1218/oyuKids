from datetime import date
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.deps import get_repo
from app.models import StudentStats
from app.navigation import ACTIVITIES, MORE, NAV, TEACHER_NAV
from app.services.classroom import due_label

BASE_DIR = Path(__file__).resolve().parent


def student_stats(student_id: int) -> StudentStats:
    return get_repo().student_stats([student_id]).get(student_id) or StudentStats()


def _layout_context(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if user is None:
        return {"user": None, "path": request.url.path}
    teacher = user.is_teacher
    return {
        "user": user,
        "stats": None if teacher else student_stats(user.id),
        "nav": TEACHER_NAV if teacher else NAV,
        "more": () if teacher else MORE,
        "path": request.url.path,
    }


templates = Jinja2Templates(directory=BASE_DIR / "templates", context_processors=[_layout_context])
templates.env.globals["activities"] = ACTIVITIES
templates.env.filters["mmss"] = lambda s: f"{int(s) // 60:02d}:{int(s) % 60:02d}"
templates.env.filters["pct"] = lambda v: f"{round((v or 0) * 100)}%"
templates.env.filters["shortdate"] = lambda d: d.strftime("%m/%d · %H:%M")
templates.env.filters["due"] = due_label
templates.env.filters["mmdd"] = lambda d: d.strftime("%m/%d")
templates.env.globals["today"] = date.today


def render(request: Request, name: str, **context):
    return templates.TemplateResponse(request, name, context)


def wants_fragment(request: Request, target: str) -> bool:
    """True for an htmx request aimed at `target` (as opposed to a boosted full-page load)."""
    return request.headers.get("HX-Target") == target


def or_404(item, what: str = "Олдсонгүй"):
    if item is None:
        raise HTTPException(status_code=404, detail=what)
    return item
