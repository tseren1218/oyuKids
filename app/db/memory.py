import uuid

from app.db import seed
from app.models import Attempt, Kid, KidStats, Passage, Poem, WordRound


class MemoryRepository:
    """In-process mock of the SingleStore repository. Data resets on restart."""

    def __init__(self) -> None:
        self._kids = {k.id: k for k in seed.KIDS}
        self._passages = {p.id: p for p in seed.PASSAGES}
        self._poems = {p.id: p for p in seed.POEMS}
        self._words = list(seed.COMPOUND_WORDS)
        self._rounds: dict[str, WordRound] = {}
        self._attempts: list[Attempt] = seed.sample_attempts()

    def get_kid(self, kid_id: int) -> Kid | None:
        return self._kids.get(kid_id)

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

    def create_word_round(self, kid_id: int, level: str, words: list[str], display_seconds: int) -> WordRound:
        word_round = WordRound(uuid.uuid4().hex, kid_id, level, words, display_seconds)
        self._rounds[word_round.id] = word_round
        return word_round

    def get_word_round(self, round_id: str) -> WordRound | None:
        return self._rounds.get(round_id)

    def save_attempt(self, attempt: Attempt) -> Attempt:
        attempt.id = max((a.id or 0 for a in self._attempts), default=0) + 1
        self._attempts.append(attempt)
        return attempt

    def list_attempts(self, kid_id: int, activity: str | None = None, limit: int = 20) -> list[Attempt]:
        rows = [a for a in self._attempts if a.kid_id == kid_id and activity in (None, a.activity)]
        return sorted(rows, key=lambda a: a.created_at, reverse=True)[:limit]

    def kid_stats(self, kid_id: int) -> KidStats:
        return KidStats.from_attempts([a for a in self._attempts if a.kid_id == kid_id])
