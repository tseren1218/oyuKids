"""Classroom views for teachers and students, assembled from repository primitives.

Each scope loads its data with a fixed handful of queries, then everything else is
computed in memory — the same code path for the mock and for SingleStore.
"""

import secrets
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from app.db.base import Repository
from app.models import Assignment, Attempt, Classroom, Membership, StudentStats, User

WORD_LEVEL_LABELS = {"easy": "Амархан", "medium": "Дунд", "hard": "Хэцүү"}
CLASSROOM_EMOJIS = ["🌻", "📚", "🚀", "🌈", "🦉", "🐳", "🍎", "⭐"]
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def new_join_code(repo: Repository) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        if repo.get_classroom_by_code(code) is None:
            return code


def item_options(repo: Repository, activity: str) -> list[tuple[str, str]]:
    if activity == "reading":
        return [(str(p.id), f"{p.emoji} {p.title}") for p in repo.list_passages()]
    if activity == "poems":
        return [(str(p.id), f"{p.emoji} {p.title} — {p.author}") for p in repo.list_poems()]
    return [(key, label) for key, label in WORD_LEVEL_LABELS.items()]


def item_title(repo: Repository, activity: str, item_id: str) -> str | None:
    if activity == "reading":
        passage = repo.get_passage(int(item_id)) if item_id.isdigit() else None
        return passage and passage.title
    if activity == "poems":
        poem = repo.get_poem(int(item_id)) if item_id.isdigit() else None
        return poem and f"«{poem.title}» шүлэг"
    return WORD_LEVEL_LABELS.get(item_id) and f"Холбоо үг · {WORD_LEVEL_LABELS[item_id]}"


def activity_url(assignment: Assignment) -> str:
    """Where a student goes to do an assignment."""
    if assignment.activity == "words":
        return f"/words?assignment={assignment.id}"
    return f"/{assignment.activity}/{assignment.item_id}?assignment={assignment.id}"


def best_by_student(attempts: list[Attempt]) -> dict[int, Attempt]:
    best: dict[int, Attempt] = {}
    for a in attempts:
        if a.student_id not in best or a.score > best[a.student_id].score:
            best[a.student_id] = a
    return best


@dataclass
class AssignmentProgress:
    assignment: Assignment
    classroom: Classroom
    roster: list[int]
    best: dict[int, Attempt]  # student id → best attempt for this assignment

    @property
    def completed(self) -> int:
        return sum(sid in self.best for sid in self.roster)

    @property
    def pct(self) -> float:
        return self.completed / len(self.roster) if self.roster else 0.0

    @property
    def avg_score(self) -> float | None:
        scores = [self.best[sid].score for sid in self.roster if sid in self.best]
        return sum(scores) / len(scores) if scores else None


@dataclass
class StudentRow:
    student: User
    status: str
    stats: StudentStats
    done: int
    total: int
    classrooms: list[Classroom]


class TeacherScope:
    def __init__(self, repo: Repository, teacher: User, classroom_id: int | None = None):
        self.teacher = teacher
        self.classrooms = repo.list_classrooms(teacher_id=teacher.id)
        if classroom_id is not None:
            self.classrooms = [c for c in self.classrooms if c.id == classroom_id]
        self.classroom_by_id = {c.id: c for c in self.classrooms}
        ids = list(self.classroom_by_id)

        self.memberships: list[Membership] = repo.list_memberships(classroom_ids=ids)
        self.assignments = repo.list_assignments(ids)
        student_ids = sorted({m.student_id for m in self.memberships})
        self.students = {u.id: u for u in repo.list_users("student") if u.id in student_ids}
        self.stats = repo.student_stats(student_ids)
        # only attempts made for this teacher's assignments — free practice is summarised in `stats`
        self.attempts = repo.list_attempts(student_ids=student_ids, assignment_ids=[a.id for a in self.assignments])

        self._attempts_by_assignment: dict[int, list[Attempt]] = defaultdict(list)
        for a in self.attempts:
            self._attempts_by_assignment[a.assignment_id].append(a)

    # roster
    def roster(self, classroom_id: int, status: str = "active") -> list[int]:
        return [m.student_id for m in self.memberships if m.classroom_id == classroom_id and m.status == status]

    @property
    def active_student_ids(self) -> set[int]:
        return {m.student_id for m in self.memberships if m.status == "active"}

    # assignments
    def progress(self, assignment: Assignment) -> AssignmentProgress:
        roster = self.roster(assignment.classroom_id)
        return AssignmentProgress(
            assignment, self.classroom_by_id[assignment.classroom_id], roster,
            best_by_student(self._attempts_by_assignment[assignment.id]),
        )

    def progress_list(self, classroom_id: int | None = None) -> list[AssignmentProgress]:
        return [self.progress(a) for a in self.assignments if classroom_id in (None, a.classroom_id)]

    def attempts_for(self, assignment_id: int) -> list[Attempt]:
        return self._attempts_by_assignment[assignment_id]

    # students
    def student_rows(self, classroom_id: int | None = None) -> list[StudentRow]:
        rows = []
        for sid, student in self.students.items():
            mine = [m for m in self.memberships if m.student_id == sid and classroom_id in (None, m.classroom_id)]
            if not mine:
                continue
            active_classes = [m.classroom_id for m in mine if m.status == "active"]
            assigned = [a for a in self.assignments if a.classroom_id in active_classes]
            done = sum(any(t.student_id == sid for t in self._attempts_by_assignment[a.id]) for a in assigned)
            status = "active" if active_classes else "invited"
            rows.append(StudentRow(student, status, self.stats.get(sid) or StudentStats(), done,
                                   len(assigned), [self.classroom_by_id[m.classroom_id] for m in mine]))
        return sorted(rows, key=lambda r: (r.status != "active", r.student.name))

    def results_matrix(self, classroom_id: int) -> list[tuple[User, list[Attempt | None]]]:
        assignments = [a for a in self.assignments if a.classroom_id == classroom_id]
        bests = {a.id: best_by_student(self._attempts_by_assignment[a.id]) for a in assignments}
        return [(self.students[sid], [bests[a.id].get(sid) for a in assignments])
                for sid in sorted(self.roster(classroom_id), key=lambda s: self.students[s].name)]

    # dashboard
    def recent_submissions(self, limit: int = 8) -> list[tuple[Attempt, User, Assignment]]:
        by_id = {a.id: a for a in self.assignments}
        rows = [a for a in self.attempts if a.assignment_id in by_id]
        return [(a, self.students[a.student_id], by_id[a.assignment_id]) for a in rows[:limit]]

    @property
    def open_assignments(self) -> list[Assignment]:
        return [a for a in self.assignments if not a.overdue]

    @property
    def completion(self) -> float:
        pairs = done = 0
        for p in self.progress_list():
            pairs += len(p.roster)
            done += p.completed
        return done / pairs if pairs else 0.0

    def needs_attention(self) -> list[tuple[User, str]]:
        """Students with overdue unfinished work or low accuracy."""
        flagged = []
        for row in self.student_rows():
            if row.status != "active":
                continue
            overdue = [p.assignment for p in self.progress_list()
                       if p.assignment.overdue and row.student.id in p.roster and row.student.id not in p.best]
            if overdue:
                flagged.append((row.student, f"Хугацаа хэтэрсэн: {overdue[0].title}"))
            elif row.stats.attempts and row.stats.avg_accuracy < 0.7:
                flagged.append((row.student, f"Дундаж нарийвчлал {round(row.stats.avg_accuracy * 100)}%"))
        return flagged


@dataclass
class StudentTask:
    assignment: Assignment
    classroom: Classroom
    best: Attempt | None

    @property
    def done(self) -> bool:
        return self.best is not None

    @property
    def url(self) -> str:
        return activity_url(self.assignment)


class StudentScope:
    def __init__(self, repo: Repository, student: User):
        self.student = student
        memberships = repo.list_memberships(student_id=student.id)
        classrooms = {c.id: c for c in repo.list_classrooms(ids=[m.classroom_id for m in memberships])}
        teachers = {u.id: u for u in repo.list_users("teacher")}

        self.classrooms = [classrooms[m.classroom_id] for m in memberships if m.status == "active"]
        self.invitations = [classrooms[m.classroom_id] for m in memberships if m.status == "invited"]
        self.teacher_of = {c.id: teachers.get(c.teacher_id) for c in classrooms.values()}

        assignments = repo.list_assignments([c.id for c in self.classrooms])
        attempts = repo.list_attempts(student_ids=[student.id], assignment_ids=[a.id for a in assignments])
        self.tasks = [
            StudentTask(a, classrooms[a.classroom_id], best_by_student([t for t in attempts if t.assignment_id == a.id]).get(student.id))
            for a in assignments
        ]

    @property
    def pending(self) -> list[StudentTask]:
        return [t for t in self.tasks if not t.done]

    @property
    def completed(self) -> list[StudentTask]:
        return [t for t in self.tasks if t.done]


def assignment_for_student(repo: Repository, student: User, assignment_id: int | None, activity: str, item_id: str) -> Assignment | None:
    """The assignment an attempt counts toward — only if the student is an active member and the item matches."""
    if not assignment_id:
        return None
    assignment = repo.get_assignment(assignment_id)
    if not assignment or assignment.activity != activity or assignment.item_id != item_id:
        return None
    member = repo.list_memberships(classroom_ids=[assignment.classroom_id], student_id=student.id)
    return assignment if member and member[0].status == "active" else None


def due_label(d: date) -> str:
    days = (d - date.today()).days
    if days < 0:
        return f"{-days} хоног хэтэрсэн"
    return {0: "Өнөөдөр", 1: "Маргааш"}.get(days, f"{days} хоногийн дараа")
