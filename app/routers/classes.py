"""Student side of classrooms: join by code, accept/decline invitations, see assignments."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from app.auth import student_required
from app.db.base import Repository
from app.deps import get_repo
from app.models import User
from app.services.classroom import StudentScope
from app.web import render

router = APIRouter(prefix="/classes", tags=["classes"])


def _page(request: Request, repo: Repository, user: User, message: str | None = None, error: str | None = None):
    return render(request, "classes/index.html", scope=StudentScope(repo, user), message=message, error=error)


@router.get("", response_class=HTMLResponse)
def index(request: Request, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    return _page(request, repo, user)


@router.post("/join", response_class=HTMLResponse)
def join(request: Request, code: str = Form(""), user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    classroom = repo.get_classroom_by_code(code.strip().upper())
    if classroom is None:
        return _page(request, repo, user, error=f"«{code}» кодтой анги олдсонгүй. Багшаасаа кодоо дахин асуугаарай.")
    repo.upsert_membership(classroom.id, user.id, "active")
    return _page(request, repo, user, message=f"🎉 «{classroom.name}» ангид нэгдлээ!")


@router.post("/{classroom_id}/accept", response_class=HTMLResponse)
def accept(request: Request, classroom_id: int, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    invited = repo.list_memberships(classroom_ids=[classroom_id], student_id=user.id)
    if invited and invited[0].status == "invited":
        repo.upsert_membership(classroom_id, user.id, "active")
        return _page(request, repo, user, message=f"🎉 «{repo.get_classroom(classroom_id).name}» ангид нэгдлээ!")
    return _page(request, repo, user)


@router.post("/{classroom_id}/decline", response_class=HTMLResponse)
def decline(request: Request, classroom_id: int, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    invited = repo.list_memberships(classroom_ids=[classroom_id], student_id=user.id)
    if invited and invited[0].status == "invited":
        repo.delete_membership(classroom_id, user.id)
    return _page(request, repo, user)
