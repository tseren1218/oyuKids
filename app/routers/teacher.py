"""Teacher area: dashboard, classrooms, students and assignments."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import teacher_required
from app.db.base import Repository
from app.deps import get_repo
from app.models import Classroom, User
from app.navigation import ACTIVITIES
from app.services.classroom import CLASSROOM_EMOJIS, TeacherScope, item_options, item_title, new_join_code
from app.web import or_404, render, wants_fragment

router = APIRouter(prefix="/teacher", tags=["teacher"], dependencies=[Depends(teacher_required)])

TABS = [("students", "🧒 Сурагчид"), ("assignments", "📋 Даалгавар"), ("results", "📈 Үр дүн")]


def _own_classroom(repo: Repository, teacher: User, classroom_id: int) -> Classroom:
    classroom = repo.get_classroom(classroom_id)
    return or_404(classroom if classroom and classroom.teacher_id == teacher.id else None)


def _assignment_form_context(repo: Repository, activity: str = "reading") -> dict:
    return {
        "activity_choices": ACTIVITIES,
        "form_activity": activity,
        "items": item_options(repo, activity),
        "default_due": (date.today() + timedelta(days=3)).isoformat(),
    }


def _create_assignment(repo, classroom_id, activity, item_id, title, due_date, instructions):
    """Returns (assignment, error)."""
    if activity not in ACTIVITIES:
        return None, "Дасгалын төрлөө сонгоно уу."
    default_title = item_title(repo, activity, item_id)
    if default_title is None:
        return None, "Даалгаврын агуулгаа сонгоно уу."
    try:
        due = date.fromisoformat(due_date)
    except ValueError:
        return None, "Дуусах огноо буруу байна."
    assignment = repo.create_assignment(classroom_id, activity, item_id, title.strip() or default_title, due, instructions.strip())
    return assignment, None


# ── dashboard ────────────────────────────────────────────────────────────────


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    scope = TeacherScope(repo, user)
    upcoming = sorted((p for p in scope.progress_list() if not p.assignment.overdue), key=lambda p: p.assignment.due_date)
    return render(request, "teacher/dashboard.html", scope=scope, upcoming=upcoming[:5])


# ── classrooms ───────────────────────────────────────────────────────────────


@router.get("/classrooms", response_class=HTMLResponse)
def classrooms(request: Request, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    return render(request, "teacher/classrooms.html", scope=TeacherScope(repo, user), emojis=CLASSROOM_EMOJIS, error=None)


@router.post("/classrooms")
def create_classroom(
    request: Request,
    name: str = Form(""),
    grade: int = Form(1),
    emoji: str = Form("🌻"),
    user: User = Depends(teacher_required),
    repo: Repository = Depends(get_repo),
):
    if not name.strip():
        return render(request, "teacher/classrooms.html", scope=TeacherScope(repo, user), emojis=CLASSROOM_EMOJIS,
                      error="Ангийн нэрээ оруулна уу.")
    classroom = repo.create_classroom(user.id, name.strip(), max(1, min(grade, 12)), emoji, new_join_code(repo))
    return RedirectResponse(f"/teacher/classrooms/{classroom.id}", status_code=303)


def _classroom_page(request, repo, user, classroom_id, tab="students", message=None, error=None, form_activity="reading"):
    classroom = _own_classroom(repo, user, classroom_id)
    scope = TeacherScope(repo, user, classroom_id=classroom.id)
    member_ids = {m.student_id for m in scope.memberships}
    context = dict(
        classroom=classroom, scope=scope, tab=tab, tabs=TABS, message=message, error=error,
        invitable=[s for s in repo.list_users("student") if s.id not in member_ids],
        **_assignment_form_context(repo, form_activity),
    )
    template = "teacher/_class_panel.html" if wants_fragment(request, "class-panel") else "teacher/classroom.html"
    return render(request, template, **context)


@router.get("/classrooms/{classroom_id}", response_class=HTMLResponse)
def classroom(request: Request, classroom_id: int, tab: str = "students", user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    return _classroom_page(request, repo, user, classroom_id, tab if tab in dict(TABS) else "students")


@router.post("/classrooms/{classroom_id}/invite", response_class=HTMLResponse)
def invite(request: Request, classroom_id: int, username: str = Form(""), user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    classroom = _own_classroom(repo, user, classroom_id)
    student = repo.get_user_by_username(username.strip().lower())
    if student is None or student.role != "student":
        return _classroom_page(request, repo, user, classroom.id, error=f"«{username}» нэртэй сурагч олдсонгүй.")
    existing = repo.list_memberships(classroom_ids=[classroom.id], student_id=student.id)
    if existing:
        state = "ангид байгаа" if existing[0].status == "active" else "урилга авсан"
        return _classroom_page(request, repo, user, classroom.id, error=f"{student.name} аль хэдийн {state}.")
    repo.upsert_membership(classroom.id, student.id, "invited")
    return _classroom_page(request, repo, user, classroom.id, message=f"✉️ {student.name}-д урилга илгээлээ.")


@router.post("/classrooms/{classroom_id}/students/{student_id}/remove", response_class=HTMLResponse)
def remove_student(request: Request, classroom_id: int, student_id: int, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    classroom = _own_classroom(repo, user, classroom_id)
    repo.delete_membership(classroom.id, student_id)
    return _classroom_page(request, repo, user, classroom.id, message="Сурагчийг ангиас хаслаа.")


@router.post("/classrooms/{classroom_id}/assignments", response_class=HTMLResponse)
def create_class_assignment(
    request: Request,
    classroom_id: int,
    activity: str = Form(""),
    item_id: str = Form(""),
    title: str = Form(""),
    due_date: str = Form(""),
    instructions: str = Form(""),
    user: User = Depends(teacher_required),
    repo: Repository = Depends(get_repo),
):
    classroom = _own_classroom(repo, user, classroom_id)
    assignment, error = _create_assignment(repo, classroom.id, activity, item_id, title, due_date, instructions)
    if error:
        return _classroom_page(request, repo, user, classroom.id, tab="assignments", error=error, form_activity=activity or "reading")
    return _classroom_page(request, repo, user, classroom.id, tab="assignments", message=f"📋 Даалгавар өглөө: {assignment.title}")


@router.get("/assignment-items", response_class=HTMLResponse)
def assignment_items(request: Request, activity: str = "reading", repo: Repository = Depends(get_repo)):
    """<option>s for the item picker; swapped in when the activity select changes."""
    return render(request, "teacher/_item_options.html", items=item_options(repo, activity))


# ── students ─────────────────────────────────────────────────────────────────


@router.get("/students", response_class=HTMLResponse)
def students(request: Request, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    return render(request, "teacher/students.html", scope=TeacherScope(repo, user))


@router.get("/students/{student_id}", response_class=HTMLResponse)
def student(request: Request, student_id: int, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    scope = TeacherScope(repo, user)
    row = or_404(next((r for r in scope.student_rows() if r.student.id == student_id), None))
    attempts = repo.list_attempts(student_ids=[student_id], limit=15)
    tasks = [(p, p.best.get(student_id)) for p in scope.progress_list() if student_id in p.roster]
    reading = list(reversed(repo.list_attempts(student_ids=[student_id], activity="reading", limit=10)))
    return render(request, "teacher/student.html", row=row, attempts=attempts, tasks=tasks, reading=reading)


# ── assignments ──────────────────────────────────────────────────────────────


@router.get("/assignments", response_class=HTMLResponse)
def assignments(request: Request, classroom: int | None = None, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    scope = TeacherScope(repo, user)
    return render(request, "teacher/assignments.html", scope=scope, selected=classroom,
                  progress=scope.progress_list(classroom), error=None, **_assignment_form_context(repo))


@router.post("/assignments")
def create_assignment(
    request: Request,
    classroom_id: int = Form(0),
    activity: str = Form(""),
    item_id: str = Form(""),
    title: str = Form(""),
    due_date: str = Form(""),
    instructions: str = Form(""),
    user: User = Depends(teacher_required),
    repo: Repository = Depends(get_repo),
):
    classroom = _own_classroom(repo, user, classroom_id)
    assignment, error = _create_assignment(repo, classroom.id, activity, item_id, title, due_date, instructions)
    if error:
        scope = TeacherScope(repo, user)
        return render(request, "teacher/assignments.html", scope=scope, selected=None, progress=scope.progress_list(),
                      error=error, **_assignment_form_context(repo, activity or "reading"))
    return RedirectResponse(f"/teacher/assignments/{assignment.id}", status_code=303)


@router.get("/assignments/{assignment_id}", response_class=HTMLResponse)
def assignment(request: Request, assignment_id: int, user: User = Depends(teacher_required), repo: Repository = Depends(get_repo)):
    a = or_404(repo.get_assignment(assignment_id))
    _own_classroom(repo, user, a.classroom_id)
    scope = TeacherScope(repo, user, classroom_id=a.classroom_id)
    progress = scope.progress(a)
    attempts = scope.attempts_for(a.id)
    rows = [
        (scope.students[sid], progress.best.get(sid), sum(t.student_id == sid for t in attempts))
        for sid in sorted(progress.roster, key=lambda s: (s not in progress.best, scope.students[s].name))
    ]
    return render(request, "teacher/assignment.html", p=progress, rows=rows)
