"""SingleStore-backed repository. Enabled with OYU_DB_BACKEND=singlestore.

`attempts` and `word_rounds` keep the original `kid_id` column name (shared with earlier
builds); it is exposed as `student_id` here. Timestamps are written by the app in local
time — the server clock is UTC.
"""

import json
import threading
import uuid
from datetime import date, datetime, time, timedelta

from app.models import Assignment, Attempt, Classroom, Membership, Passage, Poem, StudentStats, User, WordRound

USER_COLS = "id, role, username, name, avatar, grade, streak_days"
CLASSROOM_COLS = "id, teacher_id, name, grade, emoji, join_code, created_at"
ASSIGNMENT_COLS = "id, classroom_id, activity, item_id, title, due_date, instructions, created_at"
ATTEMPT_COLS = "id, kid_id AS student_id, activity, item_id, item_title, transcript, duration_ms, score, stars, wpm, details, assignment_id, audio_url, created_at"


def _json(value):
    return json.loads(value) if isinstance(value, (str, bytes)) else value


def _in(column: str, values: list) -> tuple[str, tuple]:
    return f"{column} IN ({', '.join(['%s'] * len(values))})", tuple(values)


class SingleStoreRepository:
    def __init__(self, url: str | None) -> None:
        if not url:
            raise RuntimeError("OYU_SINGLESTORE_URL is not set")
        import singlestoredb  # optional dependency: pip install '.[singlestore]'

        self._s2 = singlestoredb
        self._url = url
        self._local = threading.local()  # one connection per worker thread

    def _conn(self, fresh: bool = False):
        conn = getattr(self._local, "conn", None)
        if conn is None or fresh:
            conn = self._s2.connect(self._url, results_type="dicts", autocommit=True)
            self._local.conn = conn
        return conn

    def _execute(self, sql: str, params: tuple = ()):
        for attempt in (0, 1):
            try:
                cur = self._conn(fresh=attempt == 1).cursor()
                cur.execute(sql, params)
                return cur
            except (self._s2.OperationalError, self._s2.InterfaceError):
                if attempt == 1:
                    raise  # reconnect once (idle timeouts, network blips), then give up

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        return list(self._execute(sql, params).fetchall())

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        return self._execute(sql, params).fetchone()

    def _insert(self, sql: str, params: tuple) -> int:
        return self._execute(sql, params).lastrowid

    # users
    def get_user(self, user_id: int) -> User | None:
        row = self._one(f"SELECT {USER_COLS} FROM users WHERE id = %s", (user_id,))
        return User(**row) if row else None

    def get_user_by_username(self, username: str) -> User | None:
        row = self._one(f"SELECT {USER_COLS} FROM users WHERE username = %s", (username,))
        return User(**row) if row else None

    def list_users(self, role: str | None = None) -> list[User]:
        if role:
            return [User(**r) for r in self._all(f"SELECT {USER_COLS} FROM users WHERE role = %s ORDER BY id", (role,))]
        return [User(**r) for r in self._all(f"SELECT {USER_COLS} FROM users ORDER BY id")]

    # content
    def list_passages(self, category: str | None = None) -> list[Passage]:
        sql = "SELECT id, title, category, level, body, source, emoji FROM passages"
        rows = self._all(sql + " WHERE category = %s ORDER BY id", (category,)) if category else self._all(sql + " ORDER BY id")
        return [Passage(**r) for r in rows]

    def get_passage(self, passage_id: int) -> Passage | None:
        row = self._one("SELECT id, title, category, level, body, source, emoji FROM passages WHERE id = %s", (passage_id,))
        return Passage(**row) if row else None

    def list_poems(self) -> list[Poem]:
        return [Poem(**r) for r in self._all("SELECT id, title, author, level, body, emoji FROM poems ORDER BY level, id")]

    def get_poem(self, poem_id: int) -> Poem | None:
        row = self._one("SELECT id, title, author, level, body, emoji FROM poems WHERE id = %s", (poem_id,))
        return Poem(**row) if row else None

    def compound_words(self) -> list[str]:
        return [r["phrase"] for r in self._all("SELECT phrase FROM compound_words")]

    # classrooms & membership
    def create_classroom(self, teacher_id: int, name: str, grade: int, emoji: str, join_code: str) -> Classroom:
        new_id = self._insert(
            "INSERT INTO classrooms (teacher_id, name, grade, emoji, join_code, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (teacher_id, name, grade, emoji, join_code, datetime.now()),
        )
        return self.get_classroom(new_id)

    def get_classroom(self, classroom_id: int) -> Classroom | None:
        row = self._one(f"SELECT {CLASSROOM_COLS} FROM classrooms WHERE id = %s", (classroom_id,))
        return Classroom(**row) if row else None

    def get_classroom_by_code(self, join_code: str) -> Classroom | None:
        row = self._one(f"SELECT {CLASSROOM_COLS} FROM classrooms WHERE join_code = %s", (join_code,))
        return Classroom(**row) if row else None

    def list_classrooms(self, *, teacher_id: int | None = None, ids: list[int] | None = None) -> list[Classroom]:
        if ids == []:
            return []
        where, params = ["1 = 1"], ()
        if teacher_id is not None:
            where.append("teacher_id = %s")
            params += (teacher_id,)
        if ids is not None:
            clause, values = _in("id", ids)
            where.append(clause)
            params += values
        rows = self._all(f"SELECT {CLASSROOM_COLS} FROM classrooms WHERE {' AND '.join(where)} ORDER BY created_at", params)
        return [Classroom(**r) for r in rows]

    def upsert_membership(self, classroom_id: int, student_id: int, status: str) -> Membership:
        self._execute(
            "INSERT INTO memberships (classroom_id, student_id, status, created_at) VALUES (%s, %s, %s, %s)"
            " ON DUPLICATE KEY UPDATE status = VALUES(status)",
            (classroom_id, student_id, status, datetime.now()),
        )
        return Membership(classroom_id, student_id, status)

    def delete_membership(self, classroom_id: int, student_id: int) -> None:
        self._execute("DELETE FROM memberships WHERE classroom_id = %s AND student_id = %s", (classroom_id, student_id))

    def list_memberships(self, *, classroom_ids: list[int] | None = None, student_id: int | None = None) -> list[Membership]:
        if classroom_ids == []:
            return []
        where, params = ["1 = 1"], ()
        if classroom_ids is not None:
            clause, values = _in("classroom_id", classroom_ids)
            where.append(clause)
            params += values
        if student_id is not None:
            where.append("student_id = %s")
            params += (student_id,)
        rows = self._all(f"SELECT classroom_id, student_id, status, created_at FROM memberships WHERE {' AND '.join(where)}", params)
        return [Membership(**r) for r in rows]

    # assignments
    def create_assignment(self, classroom_id: int, activity: str, item_id: str, title: str, due_date: date, instructions: str) -> Assignment:
        new_id = self._insert(
            "INSERT INTO assignments (classroom_id, activity, item_id, title, due_date, instructions, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (classroom_id, activity, item_id, title, due_date, instructions, datetime.now()),
        )
        return self.get_assignment(new_id)

    def get_assignment(self, assignment_id: int) -> Assignment | None:
        row = self._one(f"SELECT {ASSIGNMENT_COLS} FROM assignments WHERE id = %s", (assignment_id,))
        return Assignment(**row) if row else None

    def list_assignments(self, classroom_ids: list[int]) -> list[Assignment]:
        if not classroom_ids:
            return []
        clause, params = _in("classroom_id", classroom_ids)
        rows = self._all(f"SELECT {ASSIGNMENT_COLS} FROM assignments WHERE {clause} ORDER BY due_date, id", params)
        return [Assignment(**r) for r in rows]

    # practice
    def create_word_round(self, student_id: int, level: str, words: list[str], display_seconds: int, assignment_id: int | None = None) -> WordRound:
        word_round = WordRound(uuid.uuid4().hex, student_id, level, words, display_seconds, assignment_id)
        self._execute(
            "INSERT INTO word_rounds (id, kid_id, level, words, display_seconds, assignment_id, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (word_round.id, student_id, level, json.dumps(words, ensure_ascii=False), display_seconds, assignment_id, word_round.created_at),
        )
        return word_round

    def get_attempt(self, attempt_id: int) -> Attempt | None:
        row = self._one(f"SELECT {ATTEMPT_COLS} FROM attempts WHERE id = %s", (attempt_id,))
        return Attempt(**{**row, "details": _json(row["details"]) or {}}) if row else None

    def get_word_round(self, round_id: str) -> WordRound | None:
        row = self._one(
            "SELECT id, kid_id AS student_id, level, words, display_seconds, assignment_id, created_at FROM word_rounds WHERE id = %s", (round_id,)
        )
        return WordRound(**{**row, "words": _json(row["words"])}) if row else None

    def save_attempt(self, attempt: Attempt) -> Attempt:
        attempt.id = self._insert(
            "INSERT INTO attempts (kid_id, activity, item_id, item_title, transcript, duration_ms, score, stars, wpm, details,"
            " assignment_id, audio_url, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                attempt.student_id, attempt.activity, attempt.item_id, attempt.item_title, attempt.transcript,
                attempt.duration_ms, attempt.score, attempt.stars, attempt.wpm,
                json.dumps(attempt.details, ensure_ascii=False), attempt.assignment_id, attempt.audio_url, attempt.created_at,
            ),
        )
        return attempt

    def list_attempts(self, *, student_ids=None, assignment_ids=None, activity=None, limit=None) -> list[Attempt]:
        if student_ids == [] or assignment_ids == []:
            return []
        where, params = ["1 = 1"], ()
        for column, values in (("kid_id", student_ids), ("assignment_id", assignment_ids)):
            if values is not None:
                clause, vals = _in(column, values)
                where.append(clause)
                params += vals
        if activity:
            where.append("activity = %s")
            params += (activity,)
        sql = f"SELECT {ATTEMPT_COLS} FROM attempts WHERE {' AND '.join(where)} ORDER BY created_at DESC"
        if limit:
            sql += " LIMIT %s"
            params += (limit,)
        return [Attempt(**{**r, "details": _json(r["details"]) or {}}) for r in self._all(sql, params)]

    def student_stats(self, student_ids: list[int]) -> dict[int, StudentStats]:
        # Mirrors StudentStats.from_attempts, computed server-side (thousands of attempts → one row per student).
        if not student_ids:
            return {}
        clause, params = _in("kid_id", student_ids)
        today = datetime.combine(date.today(), time.min)
        rows = self._all(
            f"""
            SELECT kid_id,
                   SUM(stars) AS total_stars,
                   COUNT(*) AS attempts,
                   MAX(CASE WHEN activity = 'reading' THEN wpm END) AS best_wpm,
                   AVG(score) AS avg_accuracy,
                   SUM(CASE WHEN activity = 'words' THEN JSON_EXTRACT_DOUBLE(details, 'recalled') END) AS words_recalled,
                   COUNT(DISTINCT CASE WHEN activity = 'poems' AND stars = 3 THEN item_id END) AS poems_mastered,
                   COUNT(DISTINCT CASE WHEN created_at >= %s AND created_at < %s THEN activity END) AS activities_today,
                   MAX(created_at) AS last_active
            FROM attempts WHERE {clause} GROUP BY kid_id
            """,
            (today, today + timedelta(days=1), *params),
        )
        return {
            r["kid_id"]: StudentStats(
                total_stars=int(r["total_stars"] or 0), attempts=int(r["attempts"]), best_wpm=float(r["best_wpm"] or 0),
                avg_accuracy=float(r["avg_accuracy"] or 0), words_recalled=int(r["words_recalled"] or 0),
                poems_mastered=int(r["poems_mastered"]), activities_today=int(r["activities_today"]), last_active=r["last_active"],
            )
            for r in rows
        }
