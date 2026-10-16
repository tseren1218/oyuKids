from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

Activity = Literal["reading", "words", "poems"]
Role = Literal["student", "teacher"]
MemberStatus = Literal["invited", "active"]


@dataclass
class User:
    id: int
    role: Role
    username: str
    name: str
    avatar: str
    grade: int | None = None  # students only
    streak_days: int = 0

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"


@dataclass
class Passage:
    id: int
    title: str
    category: str  # essay | novel | quote | tale
    level: int  # 1..3
    body: str
    source: str = ""
    emoji: str = "📖"

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    def estimated_seconds(self, wpm: int = 60) -> int:
        return max(5, round(self.word_count / wpm * 60))


@dataclass
class Poem:
    id: int
    title: str
    author: str
    level: int
    body: str
    emoji: str = "📝"

    @property
    def lines(self) -> list[str]:
        return [line.strip() for line in self.body.strip().splitlines() if line.strip()]

    @property
    def word_count(self) -> int:
        return len(self.body.split())


@dataclass
class Classroom:
    id: int
    teacher_id: int
    name: str
    grade: int
    emoji: str
    join_code: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Membership:
    classroom_id: int
    student_id: int
    status: MemberStatus
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Assignment:
    id: int
    classroom_id: int
    activity: Activity
    item_id: str  # passage id · poem id · words level key
    title: str
    due_date: date
    instructions: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def overdue(self) -> bool:
        return self.due_date < date.today()

    @property
    def days_left(self) -> int:
        return (self.due_date - date.today()).days


@dataclass
class WordRound:
    id: str
    student_id: int
    level: str
    words: list[str]
    display_seconds: int
    assignment_id: int | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Attempt:
    student_id: int
    activity: Activity
    item_id: str
    item_title: str
    transcript: str
    duration_ms: int
    score: float  # 0..1
    stars: int  # 0..3
    wpm: float | None = None
    details: dict = field(default_factory=dict)
    assignment_id: int | None = None
    audio_url: str | None = None  # s3://bucket/recordings/... (WAV) — lakehouse / oyuLLM training data
    id: int | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StudentStats:
    total_stars: int = 0
    attempts: int = 0
    best_wpm: float = 0
    avg_accuracy: float = 0
    words_recalled: int = 0
    poems_mastered: int = 0
    activities_today: int = 0
    last_active: datetime | None = None

    @classmethod
    def from_attempts(cls, attempts: list[Attempt]) -> "StudentStats":
        if not attempts:
            return cls()
        today = datetime.now().date()
        return cls(
            total_stars=sum(a.stars for a in attempts),
            attempts=len(attempts),
            best_wpm=max((a.wpm or 0 for a in attempts if a.activity == "reading"), default=0),
            avg_accuracy=sum(a.score for a in attempts) / len(attempts),
            words_recalled=sum(a.details.get("recalled", 0) for a in attempts if a.activity == "words"),
            poems_mastered=len({a.item_id for a in attempts if a.activity == "poems" and a.stars == 3}),
            activities_today=len({a.activity for a in attempts if a.created_at.date() == today}),
            last_active=max(a.created_at for a in attempts),
        )
