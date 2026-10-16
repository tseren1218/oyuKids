import random
from dataclasses import dataclass

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.auth import student_required
from app.db.base import Repository
from app.deps import get_audio_store, get_repo, get_stt
from app.models import Attempt, User
from app.services.classroom import assignment_for_student
from app.services.scoring import score_words
from app.services.recording import process_recording
from app.services.storage import AudioStore
from app.services.stt import STTProvider
from app.web import or_404, render

router = APIRouter(prefix="/words", tags=["words"])


@dataclass(frozen=True)
class Level:
    key: str
    label: str
    icon: str
    count: int
    seconds: int


LEVELS = {
    lvl.key: lvl
    for lvl in (
        Level("easy", "Амархан", "🐣", 3, 6),
        Level("medium", "Дунд", "🦊", 5, 8),
        Level("hard", "Хэцүү", "🦁", 7, 10),
    )
}


@router.get("", response_class=HTMLResponse)
def index(request: Request, assignment: int | None = None, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    task = None
    if assignment and (a := repo.get_assignment(assignment)) and a.activity == "words":
        task = assignment_for_student(repo, user, assignment, "words", a.item_id)
    return render(request, "words/index.html", levels=LEVELS.values(), selected=task.item_id if task else "easy", task=task)


@router.post("/rounds", response_class=HTMLResponse)
def start_round(
    request: Request,
    level: str = Form("easy"),
    assignment_id: int | None = Form(None),
    user: User = Depends(student_required),
    repo: Repository = Depends(get_repo),
):
    lvl = LEVELS.get(level, LEVELS["easy"])
    task = assignment_for_student(repo, user, assignment_id, "words", lvl.key)
    words = random.sample(repo.compound_words(), lvl.count)
    word_round = repo.create_word_round(user.id, lvl.key, words, lvl.seconds, task and task.id)
    return render(request, "words/_flash.html", round=word_round, level=lvl)


@router.get("/rounds/{round_id}/recall", response_class=HTMLResponse)
def recall(request: Request, round_id: str, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    word_round = _own_round(repo, round_id, user)
    return render(request, "words/_recall.html", round=word_round, level=LEVELS[word_round.level])


@router.post("/rounds/{round_id}/attempts", response_class=HTMLResponse)
async def submit(
    request: Request,
    round_id: str,
    audio: UploadFile | None = File(None),
    duration_ms: int = Form(0),
    user: User = Depends(student_required),
    repo: Repository = Depends(get_repo),
    stt: STTProvider = Depends(get_stt),
    store: AudioStore = Depends(get_audio_store),
):
    word_round = _own_round(repo, round_id, user)
    task = assignment_for_student(repo, user, word_round.assignment_id, "words", word_round.level)
    level = LEVELS[word_round.level]
    recording = await process_recording(audio, stt=stt, store=store, hint=" ".join(word_round.words), activity="words", student_id=user.id)
    transcript = recording.transcript
    result = score_words(word_round.words, transcript.text)
    repo.save_attempt(
        Attempt(
            student_id=user.id,
            activity="words",
            item_id=word_round.level,
            item_title=f"Холбоо үг · {level.label}",
            transcript=transcript.text,
            duration_ms=duration_ms,
            score=result.score,
            stars=result.stars,
            details={
                "recalled": result.recalled, "partial": result.partial, "total": result.total, "in_order": result.in_order,
                "round_id": word_round.id, "words": word_round.words,  # the reference text for this recording
            },
            assignment_id=task and task.id,
            audio_url=recording.audio_url,
        )
    )
    return render(request, "words/_result.html", round=word_round, level=level, result=result, transcript=transcript, task=task)


def _own_round(repo: Repository, round_id: str, user: User):
    word_round = or_404(repo.get_word_round(round_id))
    return or_404(word_round if word_round.student_id == user.id else None)
