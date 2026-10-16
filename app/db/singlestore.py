"""SingleStore-backed repository. Enabled with OYU_DB_BACKEND=singlestore.

Not exercised yet — wired up and ready for real credentials.
"""

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from app.models import Attempt, Kid, KidStats, Passage, Poem, WordRound


def _json(value):
    return json.loads(value) if isinstance(value, (str, bytes)) else value


class SingleStoreRepository:
    def __init__(self, url: str | None) -> None:
        if not url:
            raise RuntimeError("OYU_SINGLESTORE_URL is not set")
        import singlestoredb  # optional dependency: pip install '.[singlestore]'

        self._connect = lambda: singlestoredb.connect(url, results_type="dicts")

    @contextmanager
    def _cursor(self) -> Iterator:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        finally:
            conn.close()

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())

    def get_kid(self, kid_id: int) -> Kid | None:
        row = self._one("SELECT id, name, avatar, grade, streak_days FROM kids WHERE id = %s", (kid_id,))
        return Kid(**row) if row else None

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

    def create_word_round(self, kid_id: int, level: str, words: list[str], display_seconds: int) -> WordRound:
        word_round = WordRound(uuid.uuid4().hex, kid_id, level, words, display_seconds)
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO word_rounds (id, kid_id, level, words, display_seconds) VALUES (%s, %s, %s, %s, %s)",
                (word_round.id, kid_id, level, json.dumps(words, ensure_ascii=False), display_seconds),
            )
        return word_round

    def get_word_round(self, round_id: str) -> WordRound | None:
        row = self._one("SELECT id, kid_id, level, words, display_seconds, created_at FROM word_rounds WHERE id = %s", (round_id,))
        return WordRound(**{**row, "words": _json(row["words"])}) if row else None

    def save_attempt(self, attempt: Attempt) -> Attempt:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO attempts (kid_id, activity, item_id, item_title, transcript, duration_ms, score, stars, wpm, details)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    attempt.kid_id, attempt.activity, attempt.item_id, attempt.item_title, attempt.transcript,
                    attempt.duration_ms, attempt.score, attempt.stars, attempt.wpm,
                    json.dumps(attempt.details, ensure_ascii=False),
                ),
            )
            attempt.id = cur.lastrowid
        return attempt

    def list_attempts(self, kid_id: int, activity: str | None = None, limit: int = 20) -> list[Attempt]:
        sql = "SELECT * FROM attempts WHERE kid_id = %s"
        params: tuple = (kid_id,)
        if activity:
            sql += " AND activity = %s"
            params += (activity,)
        rows = self._all(sql + " ORDER BY created_at DESC LIMIT %s", params + (limit,))
        return [Attempt(**{**r, "details": _json(r["details"]) or {}}) for r in rows]

    def kid_stats(self, kid_id: int) -> KidStats:
        return KidStats.from_attempts(self.list_attempts(kid_id, limit=10_000))
