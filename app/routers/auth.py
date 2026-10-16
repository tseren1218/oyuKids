from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import COOKIE, authenticate, home_for, read_session, session_cookie
from app.db.base import Repository
from app.deps import get_repo
from app.web import render

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, role: str = "student", repo: Repository = Depends(get_repo)):
    user_id = read_session(request.cookies.get(COOKIE))
    if user_id and (user := repo.get_user(user_id)):
        return RedirectResponse(home_for(user), status_code=303)
    return render(request, "login.html", role=role, students=repo.list_users("student"), teachers=repo.list_users("teacher"), error=None)


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    role: str = Form("student"),
    username: str = Form(""),
    password: str = Form(""),
    repo: Repository = Depends(get_repo),
):
    user = authenticate(repo, username, password, role)
    if user is None:
        return render(
            request, "login.html", role=role, username=username,
            students=repo.list_users("student"), teachers=repo.list_users("teacher"),
            error="Ийм хэрэглэгч олдсонгүй. Доорх туршилтын хэрэглэгчээс сонгоорой.",
        )
    response = RedirectResponse(home_for(user), status_code=303)
    response.set_cookie(COOKIE, session_cookie(user.id), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE)
    return response
