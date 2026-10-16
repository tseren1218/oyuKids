from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.db.base import Repository
from app.deps import DEMO_KID_ID, get_repo, get_stt
from app.models import Attempt
from app.services.practice import LEVELS, mask_lines
from app.services.scoring import score_poem
from app.services.stt import STTProvider, transcribe_upload
from app.web import or_404, render

router = APIRouter(prefix="/poems", tags=["poems"])


@router.get("", response_class=HTMLResponse)
def index(request: Request, repo: Repository = Depends(get_repo)):
    return render(request, "poems/index.html", poems=repo.list_poems())


@router.get("/{poem_id}", response_class=HTMLResponse)
def detail(request: Request, poem_id: int, repo: Repository = Depends(get_repo)):
    poem = or_404(repo.get_poem(poem_id))
    return render(request, "poems/detail.html", poem=poem, levels=LEVELS, level=0, seed=0, lines=mask_lines(poem.lines, 0))


@router.get("/{poem_id}/practice", response_class=HTMLResponse)
def practice(request: Request, poem_id: int, level: int = 0, seed: int = 0, repo: Repository = Depends(get_repo)):
    poem = or_404(repo.get_poem(poem_id))
    return render(request, "poems/_practice.html", poem=poem, levels=LEVELS, level=level, seed=seed, lines=mask_lines(poem.lines, level, seed))


@router.get("/{poem_id}/recite", response_class=HTMLResponse)
def recite(request: Request, poem_id: int, repo: Repository = Depends(get_repo)):
    poem = or_404(repo.get_poem(poem_id))
    return render(request, "poems/_recite.html", poem=poem, levels=LEVELS)


@router.post("/{poem_id}/attempts", response_class=HTMLResponse)
async def submit(
    request: Request,
    poem_id: int,
    audio: UploadFile | None = File(None),
    duration_ms: int = Form(0),
    repo: Repository = Depends(get_repo),
    stt: STTProvider = Depends(get_stt),
):
    poem = or_404(repo.get_poem(poem_id))
    transcript = await transcribe_upload(stt, audio, hint=poem.body)
    result = score_poem(poem.body, transcript.text)
    repo.save_attempt(
        Attempt(
            kid_id=DEMO_KID_ID,
            activity="poems",
            item_id=str(poem.id),
            item_title=poem.title,
            transcript=transcript.text,
            duration_ms=duration_ms,
            score=result.accuracy,
            stars=result.stars,
        )
    )
    return render(request, "poems/_result.html", poem=poem, levels=LEVELS, result=result, transcript=transcript)
