import copy
import uuid
from datetime import date

from app.db import seed
from app.models import Assignment, Attempt, Classroom, Membership, Passage, Poem, StudentStats, User, WordRound


def _match(value, allowed: list | None) -> bool:
    return allowed is None or value in allowed


class MemoryRepository:
    """In-process mock of the SingleStore repository. Data resets on restart."""

    def __init__(self) -> None:
        self._users = {u.id: u for u in copy.deepcopy(seed.USERS)}
        self._passages = {p.id: p for p in seed.PASSAGES}
        self._poems = {p.id: p for p in seed.POEMS}
        self._words = list(seed.COMPOUND_WORDS)
        self._classrooms = {c.id: c for c in copy.deepcopy(seed.CLASSROOMS)}
        self._memberships = {(m.classroom_id, m.student_id): m for m in copy.deepcopy(seed.MEMBERSHIPS)}
        self._assignments = {a.id: a for a in copy.deepcopy(seed.ASSIGNMENTS)}
        self._rounds: dict[str, WordRound] = {}
        self._attempts: list[Attempt] = seed.sample_attempts()

    # users
    def get_user(self, user_id: int) -> User | None:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        return next((u for u in self._users.values() if u.username == username), None)

    def list_users(self, role: str | None = None) -> list[User]:
        return [u for u in self._users.values() if role in (None, u.role)]

    # content
    def list_passages(self, category: str | None = None) -> list[Passage]:
        return [p for p in self._passages.values() if category in (None, p.category)]

    def get_passage(self, passage_id: int) -> Passage | None:
        return self._passages.get(passage_id)

    def list_poems(self) -> list[Poem]:
        return list(self._poems.values())

    def get_poem(self, poem_id: int) -> Poem | None:
        return self._poems.get(poem_id)

    def compound_words(self) -> list[str]:
        return list(self._words)

    # classrooms & membership
    def create_classroom(self, teacher_id: int, name: str, grade: int, emoji: str, join_code: str) -> Classroom:
        classroom = Classroom(max(self._classrooms, default=0) + 1, teacher_id, name, grade, emoji, join_code)
        self._classrooms[classroom.id] = classroom
        return classroom

    def get_classroom(self, classroom_id: int) -> Classroom | None:
        return self._classrooms.get(classroom_id)

    def get_classroom_by_code(self, join_code: str) -> Classroom | None:
        return next((c for c in self._classrooms.values() if c.join_code == join_code), None)

    def list_classrooms(self, *, teacher_id: int | None = None, ids: list[int] | None = None) -> list[Classroom]:
        rows = [c for c in self._classrooms.values() if teacher_id in (None, c.teacher_id) and _match(c.id, ids)]
        return sorted(rows, key=lambda c: c.created_at)

    def upsert_membership(self, classroom_id: int, student_id: int, status: str) -> Membership:
        key = (classroom_id, student_id)
        if key in self._memberships:
            self._memberships[key].status = status
        else:
            self._memberships[key] = Membership(classroom_id, student_id, status)
        return self._memberships[key]

    def delete_membership(self, classroom_id: int, student_id: int) -> None:
        self._memberships.pop((classroom_id, student_id), None)

    def list_memberships(self, *, classroom_ids: list[int] | None = None, student_id: int | None = None) -> list[Membership]:
        return [
            m for m in self._memberships.values()
            if _match(m.classroom_id, classroom_ids) and student_id in (None, m.student_id)
        ]

    # assignments
    def create_assignment(self, classroom_id: int, activity: str, item_id: str, title: str, due_date: date, instructions: str) -> Assignment:
        assignment = Assignment(max(self._assignments, default=0) + 1, classroom_id, activity, item_id, title, due_date, instructions)
        self._assignments[assignment.id] = assignment
        return assignment

    def get_assignment(self, assignment_id: int) -> Assignment | None:
        return self._assignments.get(assignment_id)

    def list_assignments(self, classroom_ids: list[int]) -> list[Assignment]:
        rows = [a for a in self._assignments.values() if a.classroom_id in classroom_ids]
        return sorted(rows, key=lambda a: (a.due_date, a.id))

    # practice
    def create_word_round(self, student_id: int, level: str, words: list[str], display_seconds: int, assignment_id: int | None = None) -> WordRound:
        word_round = WordRound(uuid.uuid4().hex, student_id, level, words, display_seconds, assignment_id)
        self._rounds[word_round.id] = word_round
        return word_round

    def get_attempt(self, attempt_id: int) -> Attempt | None:
        return next((a for a in self._attempts if a.id == attempt_id), None)

    def get_word_round(self, round_id: str) -> WordRound | None:
        return self._rounds.get(round_id)

    def save_attempt(self, attempt: Attempt) -> Attempt:
        attempt.id = max((a.id or 0 for a in self._attempts), default=0) + 1
        self._attempts.append(attempt)
        return attempt

    def list_attempts(self, *, student_ids=None, assignment_ids=None, activity=None, limit=None) -> list[Attempt]:
        rows = [
            a for a in self._attempts
            if _match(a.student_id, student_ids) and _match(a.assignment_id, assignment_ids) and activity in (None, a.activity)
        ]
        rows.sort(key=lambda a: a.created_at, reverse=True)
        return rows[:limit] if limit else rows

    def student_stats(self, student_ids: list[int]) -> dict[int, StudentStats]:
        stats = {}
        for sid in student_ids:
            attempts = [a for a in self._attempts if a.student_id == sid]
            if attempts:
                stats[sid] = StudentStats.from_attempts(attempts)
        return stats
