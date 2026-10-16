from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.db.base import Repository
from app.deps import DEMO_KID_ID, get_repo, get_stt
from app.models import Attempt
from app.services.scoring import score_reading
from app.services.stt import STTProvider, transcribe_upload
from app.web import or_404, render, wants_fragment

router = APIRouter(prefix="/reading", tags=["reading"])

CATEGORIES = [
    ("", "Бүгд", "✨"),
    ("essay", "Эссэ", "📰"),
    ("novel", "Роман", "📚"),
    ("tale", "Өгүүллэг", "🧚"),
    ("quote", "Ишлэл", "💬"),
]
CATEGORY_LABELS = {key: label for key, label, _ in CATEGORIES}


@router.get("", response_class=HTMLResponse)
def index(request: Request, category: str = "", repo: Repository = Depends(get_repo)):
    template = "reading/_passage_list.html" if wants_fragment(request, "passage-list") else "reading/index.html"
    return render(
        request,
        template,
        passages=repo.list_passages(category or None),
        categories=CATEGORIES,
        category_labels=CATEGORY_LABELS,
        category=category,
    )


@router.get("/{passage_id}", response_class=HTMLResponse)
def detail(request: Request, passage_id: int, repo: Repository = Depends(get_repo)):
    passage = or_404(repo.get_passage(passage_id))
    return render(request, "reading/detail.html", passage=passage, category_labels=CATEGORY_LABELS)


@router.post("/{passage_id}/attempts", response_class=HTMLResponse)
async def submit(
    request: Request,
    passage_id: int,
    audio: UploadFile | None = File(None),
    duration_ms: int = Form(0),
    repo: Repository = Depends(get_repo),
    stt: STTProvider = Depends(get_stt),
):
    passage = or_404(repo.get_passage(passage_id))
    transcript = await transcribe_upload(stt, audio, hint=passage.body)
    duration = transcript.duration_seconds or duration_ms / 1000
    result = score_reading(passage.body, transcript.text, duration)
    repo.save_attempt(
        Attempt(
            kid_id=DEMO_KID_ID,
            activity="reading",
            item_id=str(passage.id),
            item_title=passage.title,
            transcript=transcript.text,
            duration_ms=round(duration * 1000),
            score=result.accuracy,
            stars=result.stars,
            wpm=result.wpm,
        )
    )
    return render(request, "reading/_result.html", passage=passage, result=result, transcript=transcript)
