"""Compare what the child said (STT transcript) with the expected text."""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

CLOSE_RATIO = 0.75  # words at least this similar count as "close enough" (accent, STT spelling)
_WORD = re.compile(r"\w+")


def normalize(token: str) -> str:
    return "".join(_WORD.findall(token.lower())).replace("ё", "е")


def similar(a: str, b: str) -> bool:
    return a == b or SequenceMatcher(None, a, b).ratio() >= CLOSE_RATIO


def stars_for(score: float) -> int:
    return 3 if score >= 0.95 else 2 if score >= 0.8 else 1 if score >= 0.5 else 0


CHEERS = {
    3: "Гайхалтай! Чи жинхэнэ од байна!",
    2: "Маш сайн! Жаахан дасгал хийвэл төгс болно.",
    1: "Сайн эхлэл! Дахиад нэг оролдоод үзье.",
    0: "Санаа зоволтгүй, дахин оролдвол заавал чадна!",
}


# ── Text alignment (reading + poems) ─────────────────────────────────────────


@dataclass
class Token:
    text: str  # as displayed, with punctuation
    norm: str
    line: int
    status: str = "missed"  # correct | close | wrong | missed | skip
    heard: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("correct", "close")


@dataclass
class Alignment:
    tokens: list[Token]
    extra_words: int = 0
    heard_words: int = 0

    @property
    def scored(self) -> list[Token]:
        return [t for t in self.tokens if t.status != "skip"]

    @property
    def total(self) -> int:
        return len(self.scored)

    @property
    def correct(self) -> int:
        return sum(t.ok for t in self.scored)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def count(self, status: str) -> int:
        return sum(t.status == status for t in self.tokens)

    @property
    def lines(self) -> list[list[Token]]:
        grouped: dict[int, list[Token]] = {}
        for t in self.tokens:
            grouped.setdefault(t.line, []).append(t)
        return [grouped[k] for k in sorted(grouped)]


def align(reference: str, hypothesis: str) -> Alignment:
    tokens = [
        Token(raw, normalize(raw), line_no)
        for line_no, line in enumerate(l for l in reference.strip().splitlines() if l.strip())
        for raw in line.split()
    ]
    for t in tokens:
        if not t.norm:
            t.status = "skip"  # standalone punctuation such as «—»
    scored = [t for t in tokens if t.norm]
    heard = [n for n in map(normalize, hypothesis.split()) if n]

    extra = 0
    matcher = SequenceMatcher(None, [t.norm for t in scored], heard, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for t in scored[i1:i2]:
                t.status = "correct"
        elif op == "insert":
            extra += j2 - j1
        elif op == "replace":
            for t, h in zip(scored[i1:i2], heard[j1:j2]):
                t.heard = h
                t.status = "close" if similar(t.norm, h) else "wrong"
            extra += max(0, (j2 - j1) - (i2 - i1))
        # "delete": reference words stay "missed"
    return Alignment(tokens, extra_words=extra, heard_words=len(heard))


# ── Reading (WPM) ────────────────────────────────────────────────────────────

WPM_BANDS = [(100, "Аянга", "⚡"), (70, "Хурдан", "🚀"), (40, "Дунд", "🚲"), (0, "Эхлэгч", "🐢")]
WPM_GAUGE_MAX = 120


@dataclass
class ReadingResult:
    alignment: Alignment
    duration_seconds: float
    wpm: float  # correctly read words per minute

    @property
    def accuracy(self) -> float:
        return self.alignment.accuracy

    @property
    def stars(self) -> int:
        return stars_for(self.accuracy)

    @property
    def cheer(self) -> str:
        return CHEERS[self.stars]

    @property
    def band(self) -> tuple[str, str]:
        return next((label, icon) for floor, label, icon in WPM_BANDS if self.wpm >= floor)

    @property
    def gauge(self) -> float:
        return min(self.wpm / WPM_GAUGE_MAX, 1.0)


def score_reading(reference: str, transcript: str, duration_seconds: float) -> ReadingResult:
    alignment = align(reference, transcript)
    minutes = duration_seconds / 60
    wpm = alignment.correct / minutes if minutes > 0 else 0.0
    return ReadingResult(alignment, duration_seconds, round(wpm, 1))


# ── Poems ────────────────────────────────────────────────────────────────────


@dataclass
class PoemResult:
    alignment: Alignment

    @property
    def accuracy(self) -> float:
        return self.alignment.accuracy

    @property
    def stars(self) -> int:
        return stars_for(self.accuracy)

    @property
    def cheer(self) -> str:
        return CHEERS[self.stars]

    @property
    def lines(self) -> list[tuple[list[Token], float]]:
        out = []
        for line in self.alignment.lines:
            scored = [t for t in line if t.status != "skip"]
            out.append((line, sum(t.ok for t in scored) / len(scored) if scored else 1.0))
        return out


def score_poem(poem_body: str, transcript: str) -> PoemResult:
    return PoemResult(align(poem_body, transcript))


# ── Compound-word recall ─────────────────────────────────────────────────────


@dataclass
class RecallItem:
    phrase: str
    status: str  # recalled | partial | missed
    position: int | None = None  # where in the transcript it was heard


@dataclass
class WordsResult:
    items: list[RecallItem] = field(default_factory=list)
    in_order: int = 0  # recalled phrases said in the shown order

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def recalled(self) -> int:
        return sum(i.status == "recalled" for i in self.items)

    @property
    def partial(self) -> int:
        return sum(i.status == "partial" for i in self.items)

    @property
    def score(self) -> float:
        return (self.recalled + 0.5 * self.partial) / self.total if self.total else 0.0

    @property
    def perfect_order(self) -> bool:
        return self.recalled == self.total and self.in_order == self.total

    @property
    def stars(self) -> int:
        return stars_for(self.score)

    @property
    def cheer(self) -> str:
        return CHEERS[self.stars]


def _longest_increasing(values: list[int]) -> int:
    best = [1] * len(values)
    for i in range(len(values)):
        for j in range(i):
            if values[j] < values[i]:
                best[i] = max(best[i], best[j] + 1)
    return max(best, default=0)


def score_words(phrases: list[str], transcript: str) -> WordsResult:
    heard = [n for n in map(normalize, transcript.split()) if n]
    used: set[int] = set()
    result = WordsResult()
    for phrase in phrases:
        parts = [normalize(p) for p in phrase.split()]
        position = next(
            (
                i
                for i in range(len(heard) - len(parts) + 1)
                if not used & set(range(i, i + len(parts)))
                and all(similar(heard[i + k], part) for k, part in enumerate(parts))
            ),
            None,
        )
        if position is not None:
            used.update(range(position, position + len(parts)))
            result.items.append(RecallItem(phrase, "recalled", position))
        elif any(similar(h, part) for h in heard for part in parts):
            result.items.append(RecallItem(phrase, "partial"))
        else:
            result.items.append(RecallItem(phrase, "missed"))
    result.in_order = _longest_increasing([i.position for i in result.items if i.position is not None])
    return result
