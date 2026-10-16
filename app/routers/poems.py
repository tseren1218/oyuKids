from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.auth import student_required
from app.db.base import Repository
from app.deps import get_audio_store, get_repo, get_stt
from app.models import Attempt, User
from app.services.classroom import assignment_for_student
from app.services.practice import LEVELS, mask_lines
from app.services.scoring import score_poem
from app.services.recording import process_recording
from app.services.storage import AudioStore
from app.services.stt import STTProvider
from app.web import or_404, render

router = APIRouter(prefix="/poems", tags=["poems"])


@router.get("", response_class=HTMLResponse)
def index(request: Request, user: User = Depends(student_required), repo: Repository = Depends(get_repo)):
    return render(request, "poems/index.html", poems=repo.list_poems())


@router.get("/{poem_id}", response_class=HTMLResponse)
def detail(
    request: Request, poem_id: int, assignment: int | None = None,
    user: User = Depends(student_required), repo: Repository = Depends(get_repo),
):
    poem = or_404(repo.get_poem(poem_id))
    task = assignment_for_student(repo, user, assignment, "poems", str(poem.id))
    return render(request, "poems/detail.html", poem=poem, levels=LEVELS, level=0, seed=0, lines=mask_lines(poem.lines, 0), task=task)


@router.get("/{poem_id}/practice", response_class=HTMLResponse)
def practice(
    request: Request, poem_id: int, level: int = 0, seed: int = 0, assignment: int | None = None,
    user: User = Depends(student_required), repo: Repository = Depends(get_repo),
):
    poem = or_404(repo.get_poem(poem_id))
    task = assignment_for_student(repo, user, assignment, "poems", str(poem.id))
    lines = mask_lines(poem.lines, level, seed)
    return render(request, "poems/_practice.html", poem=poem, levels=LEVELS, level=level, seed=seed, lines=lines, task=task)


@router.get("/{poem_id}/recite", response_class=HTMLResponse)
def recite(
    request: Request, poem_id: int, assignment: int | None = None,
    user: User = Depends(student_required), repo: Repository = Depends(get_repo),
):
    poem = or_404(repo.get_poem(poem_id))
    task = assignment_for_student(repo, user, assignment, "poems", str(poem.id))
    return render(request, "poems/_recite.html", poem=poem, levels=LEVELS, task=task)


@router.post("/{poem_id}/attempts", response_class=HTMLResponse)
async def submit(
    request: Request,
    poem_id: int,
    audio: UploadFile | None = File(None),
    duration_ms: int = Form(0),
    assignment_id: int | None = Form(None),
    user: User = Depends(student_required),
    repo: Repository = Depends(get_repo),
    stt: STTProvider = Depends(get_stt),
    store: AudioStore = Depends(get_audio_store),
):
    poem = or_404(repo.get_poem(poem_id))
    task = assignment_for_student(repo, user, assignment_id, "poems", str(poem.id))
    recording = await process_recording(audio, stt=stt, store=store, hint=poem.body, activity="poems", student_id=user.id)
    transcript = recording.transcript
    result = score_poem(poem.body, transcript.text)
    repo.save_attempt(
        Attempt(
            student_id=user.id,
            activity="poems",
            item_id=str(poem.id),
            item_title=poem.title,
            transcript=transcript.text,
            duration_ms=duration_ms,
            score=result.accuracy,
            stars=result.stars,
            assignment_id=task and task.id,
            audio_url=recording.audio_url,
        )
    )
    return render(request, "poems/_result.html", poem=poem, levels=LEVELS, result=result, transcript=transcript, task=task)
