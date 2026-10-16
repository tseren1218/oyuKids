"""Mock authentication: pick a user, get a signed session cookie. No passwords yet.

Swap `authenticate` for a real check later; the cookie and the role guards stay the same.
"""

import hashlib
import hmac

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.config import get_settings
from app.db.base import Repository
from app.deps import get_repo
from app.models import User

COOKIE = "oyu_session"


class LoginRequired(Exception):
    pass


class WrongRole(Exception):
    def __init__(self, user: User):
        self.user = user


def _sign(value: str) -> str:
    return hmac.new(get_settings().session_secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def session_cookie(user_id: int) -> str:
    return f"{user_id}.{_sign(str(user_id))}"


def read_session(cookie: str | None) -> int | None:
    if not cookie or "." not in cookie:
        return None
    user_id, signature = cookie.split(".", 1)
    return int(user_id) if user_id.isdigit() and hmac.compare_digest(signature, _sign(user_id)) else None


def authenticate(repo: Repository, username: str, password: str, role: str) -> User | None:
    user = repo.get_user_by_username(username.strip().lower())
    return user if user and user.role == role else None  # mock: any password works


def home_for(user: User) -> str:
    return "/teacher" if user.is_teacher else "/"


def current_user(request: Request, repo: Repository = Depends(get_repo)) -> User:
    user_id = read_session(request.cookies.get(COOKIE))
    user = repo.get_user(user_id) if user_id else None
    if user is None:
        raise LoginRequired()
    request.state.user = user  # for the template context processor
    return user


def student_required(user: User = Depends(current_user)) -> User:
    if user.role != "student":
        raise WrongRole(user)
    return user


def teacher_required(user: User = Depends(current_user)) -> User:
    if user.role != "teacher":
        raise WrongRole(user)
    return user


def _redirect(request: Request, url: str) -> Response:
    if request.headers.get("HX-Request"):
        return Response(status_code=204, headers={"HX-Redirect": url})
    return RedirectResponse(url, status_code=303)


async def on_login_required(request: Request, exc: LoginRequired) -> Response:
    return _redirect(request, "/login")


async def on_wrong_role(request: Request, exc: WrongRole) -> Response:
    return _redirect(request, home_for(exc.user))
