import random
from dataclasses import dataclass

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.db.base import Repository
from app.deps import DEMO_KID_ID, get_repo, get_stt
from app.models import Attempt
from app.services.scoring import score_words
from app.services.stt import STTProvider, transcribe_upload
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
def index(request: Request):
    return render(request, "words/index.html", levels=LEVELS.values(), selected="easy")


@router.post("/rounds", response_class=HTMLResponse)
def start_round(request: Request, level: str = Form("easy"), repo: Repository = Depends(get_repo)):
    lvl = LEVELS.get(level, LEVELS["easy"])
    words = random.sample(repo.compound_words(), lvl.count)
    word_round = repo.create_word_round(DEMO_KID_ID, lvl.key, words, lvl.seconds)
    return render(request, "words/_flash.html", round=word_round, level=lvl)


@router.get("/rounds/{round_id}/recall", response_class=HTMLResponse)
def recall(request: Request, round_id: str, repo: Repository = Depends(get_repo)):
    word_round = or_404(repo.get_word_round(round_id))
    return render(request, "words/_recall.html", round=word_round, level=LEVELS[word_round.level])


@router.post("/rounds/{round_id}/attempts", response_class=HTMLResponse)
async def submit(
    request: Request,
    round_id: str,
    audio: UploadFile | None = File(None),
    duration_ms: int = Form(0),
    repo: Repository = Depends(get_repo),
    stt: STTProvider = Depends(get_stt),
):
    word_round = or_404(repo.get_word_round(round_id))
    level = LEVELS[word_round.level]
    transcript = await transcribe_upload(stt, audio, hint=" ".join(word_round.words))
    result = score_words(word_round.words, transcript.text)
    repo.save_attempt(
        Attempt(
            kid_id=DEMO_KID_ID,
            activity="words",
            item_id=word_round.id,
            item_title=f"Холбоо үг · {level.label}",
            transcript=transcript.text,
            duration_ms=duration_ms,
            score=result.score,
            stars=result.stars,
            details={"recalled": result.recalled, "partial": result.partial, "total": result.total, "in_order": result.in_order},
        )
    )
    return render(request, "words/_result.html", round=word_round, level=level, result=result, transcript=transcript)
