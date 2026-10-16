import re

import pytest

from app.auth import COOKIE, session_cookie

PANEL = {"HX-Request": "true", "HX-Target": "class-panel"}


def alert(html: str) -> str:
    return re.search(r'class="alert alert--\w+">(.*?)<', html).group(1)


# ── auth ─────────────────────────────────────────────────────────────────────


def test_anonymous_is_sent_to_login(client):
    res = client.get("/", follow_redirects=False)
    assert (res.status_code, res.headers["location"]) == (303, "/login")
    htmx = client.get("/teacher", headers={"HX-Request": "true"}, follow_redirects=False)
    assert htmx.headers["HX-Redirect"] == "/login"


def test_login_routes_by_role(client, login):
    assert login("nomin", "student").get("/", follow_redirects=False).status_code == 200
    assert login("sarnai", "teacher").get("/", follow_redirects=False).headers["location"] == "/teacher"


def test_login_rejects_unknown_user_and_wrong_role(client):
    assert "олдсонгүй" in client.post("/login", data={"username": "nobody", "role": "student"}).text
    assert "олдсонгүй" in client.post("/login", data={"username": "sarnai", "role": "student"}).text


def test_forged_cookie_is_rejected(client):
    client.cookies.set(COOKIE, "101.forged")
    assert client.get("/teacher", follow_redirects=False).headers["location"] == "/login"
    client.cookies.set(COOKIE, session_cookie(101))
    assert client.get("/teacher").status_code == 200


def test_roles_are_separated(student, login):
    assert student.get("/teacher", follow_redirects=False).headers["location"] == "/"
    teacher = login("sarnai", "teacher")
    assert teacher.get("/reading", follow_redirects=False).headers["location"] == "/teacher"


def test_logout(student):
    student.post("/logout")
    assert student.get("/", follow_redirects=False).headers["location"] == "/login"


# ── teacher pages ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", [
    "/teacher", "/teacher/classrooms", "/teacher/classrooms/1", "/teacher/classrooms/1?tab=assignments",
    "/teacher/classrooms/1?tab=results", "/teacher/students", "/teacher/students/1", "/teacher/assignments",
    "/teacher/assignments?classroom=2", "/teacher/assignments/1",
])
def test_teacher_pages_render(teacher, path):
    assert teacher.get(path).status_code == 200


def test_teacher_cannot_see_other_teachers_classes(teacher):
    assert teacher.get("/teacher/classrooms/3").status_code == 404  # belongs to Бат багш
    assert teacher.get("/teacher/assignments/5").status_code == 404
    assert teacher.get("/teacher/students/2").status_code == 200
    assert teacher.post("/teacher/classrooms/3/invite", data={"username": "nomin"}).status_code == 404


def test_dashboard_summarises_seed_data(teacher):
    html = teacher.get("/teacher").text
    assert "Удахгүй дуусах даалгавар" in html and "Сүүлийн илгээлтүүд" in html
    assert "Билгүүн" in html  # flagged: low score on the overdue words task


# ── full loop: create → invite/join → assign → submit → results ──────────────


def test_classroom_lifecycle(teacher, login):
    res = teacher.post("/teacher/classrooms", data={"name": "Туршилт", "grade": "2", "emoji": "🐳"}, follow_redirects=False)
    classroom_id = int(res.headers["location"].rsplit("/", 1)[1])
    page = teacher.get(f"/teacher/classrooms/{classroom_id}").text
    code = re.search(r'<code class="code-chip">(\w{6})</code>', page).group(1)

    assert "урилга илгээлээ" in alert(teacher.post(f"/teacher/classrooms/{classroom_id}/invite", data={"username": "ganzorig"}, headers=PANEL).text)
    assert "аль хэдийн" in alert(teacher.post(f"/teacher/classrooms/{classroom_id}/invite", data={"username": "ganzorig"}, headers=PANEL).text)
    assert "олдсонгүй" in alert(teacher.post(f"/teacher/classrooms/{classroom_id}/invite", data={"username": "sarnai"}, headers=PANEL).text)

    res = teacher.post(f"/teacher/classrooms/{classroom_id}/assignments", headers=PANEL,
                       data={"activity": "reading", "item_id": "2", "title": "", "due_date": "2030-01-01", "instructions": ""})
    assert res.text.lstrip().startswith('<div id="class-panel">')
    assert "Хаврын өглөө" in alert(res.text)
    assignment_id = int(re.findall(r'href="/teacher/assignments/(\d+)"', res.text)[0])

    # invited student accepts; another joins with the code (case-insensitive)
    ganzorig = login("ganzorig", "student")
    assert "ангид урьж байна" in ganzorig.get("/").text
    ganzorig.post(f"/classes/{classroom_id}/accept")
    assert f"/reading/2?assignment={assignment_id}" in ganzorig.get("/classes").text

    nomin = login("nomin", "student")
    assert "нэгдлээ" in alert(nomin.post("/classes/join", data={"code": code.lower()}).text)
    result = nomin.post("/reading/2/attempts", data={"duration_ms": "20000", "assignment_id": str(assignment_id)},
                        files={"audio": ("a.webm", b"", "audio/webm")})
    assert "Даалгавар илгээгдлээ" in result.text

    teacher = login("sarnai", "teacher")
    detail = teacher.get(f"/teacher/assignments/{assignment_id}").text
    assert detail.count("✅ Хийсэн") == 1 and "<b>1/2</b>" in detail


def test_attempt_only_counts_for_matching_active_assignment(student, login):
    # assignment 4 is reading passage 3 in a class Номин belongs to; passage 1 doesn't match it
    res = student.post("/reading/1/attempts", data={"duration_ms": "20000", "assignment_id": "4"}, files={"audio": ("a.webm", b"", "audio/webm")})
    assert "Даалгавар илгээгдлээ" not in res.text
    # Ганзориг is only *invited* to 3А, so its assignment doesn't count yet
    ganzorig = login("ganzorig", "student")
    res = ganzorig.post("/reading/1/attempts", data={"duration_ms": "20000", "assignment_id": "1"}, files={"audio": ("a.webm", b"", "audio/webm")})
    assert "Даалгавар илгээгдлээ" not in res.text


def test_words_assignment_locks_level(student):
    page = student.get("/words?assignment=3").text
    assert page.count('name="level"') == 1 and 'value="medium"' in page
    flash = student.post("/words/rounds", data={"level": "medium", "assignment_id": "3"})
    round_id = re.search(r"/words/rounds/(\w+)/recall", flash.text).group(1)
    assert "Даалгавар илгээгдлээ" in student.post(f"/words/rounds/{round_id}/attempts", data={"duration_ms": "8000"}).text


def test_remove_student_and_decline_invite(teacher, login):
    res = teacher.post("/teacher/classrooms/1/students/2/remove", headers=PANEL)
    assert "хаслаа" in alert(res.text) and "/teacher/students/2" not in res.text  # gone from roster…
    assert '<option value="temuulen">' in res.text  # …and invitable again
    ganzorig = login("ganzorig", "student")
    ganzorig.post("/classes/1/decline")
    assert "ангид урьж байна" not in ganzorig.get("/").text


def test_assignment_validation(teacher):
    res = teacher.post("/teacher/assignments", data={"classroom_id": "1", "activity": "poems", "item_id": "999", "due_date": "2030-01-01"})
    assert "агуулгаа сонгоно" in res.text
    res = teacher.post("/teacher/assignments", data={"classroom_id": "1", "activity": "words", "item_id": "hard", "due_date": "2030-01-01"},
                       follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"].startswith("/teacher/assignments/")
    options = teacher.get("/teacher/assignment-items?activity=poems").text
    assert options.count("<option") == 3
