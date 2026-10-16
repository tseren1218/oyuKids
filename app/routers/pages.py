from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth import student_required
from app.db.base import Repository
from app.deps import get_repo
from app.models import User
from app.navigation import MODULES, MORE, MORE_BY_SLUG
from app.services.classroom import StudentScope
from app.web import or_404, render, student_stats

router = APIRouter(tags=["pages"])

DAILY_GOAL = 3


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    stats = student_stats(user.id)
    module_stats = {
        "reading": f"Шилдэг: {stats.best_wpm:.0f} үг/мин",
        "words": f"Санасан: {stats.words_recalled} үг",
        "poems": f"Цээжилсэн: {stats.poems_mastered} шүлэг",
    }
    return render(
        request,
        "home.html",
        modules=[(m, module_stats[m.key]) for m in MODULES],
        recent=repo.list_attempts(student_ids=[user.id], limit=5),
        scope=StudentScope(repo, user),
        soon=MORE[:4],
        daily_goal=DAILY_GOAL,
    )


@router.get("/progress", response_class=HTMLResponse)
def progress(request: Request, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    reading = list(reversed(repo.list_attempts(student_ids=[user.id], activity="reading", limit=10)))
    return render(request, "progress.html", attempts=repo.list_attempts(student_ids=[user.id], limit=30), reading=reading)


@router.get("/soon/{slug}", response_class=HTMLResponse)
def coming_soon(request: Request, slug: str, user: User = Depends(student_required)):
    return render(request, "coming_soon.html", item=or_404(MORE_BY_SLUG.get(slug)))
