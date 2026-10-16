"""One submitted recording → transcript (+ stored WAV), shared by every activity."""

import asyncio
from dataclasses import dataclass

from fastapi import UploadFile

from app.services.storage import AudioStore
from app.services.stt import MockSTT, STTProvider, Transcript

_demo_stt = MockSTT()


@dataclass
class Recording:
    transcript: Transcript
    audio_url: str | None  # s3://… when stored


async def process_recording(
    upload: UploadFile | None,
    *,
    stt: STTProvider,
    store: AudioStore,
    hint: str,
    activity: str,
    student_id: int,
) -> Recording:
    audio = await upload.read() if upload else b""
    mime_type = (upload.content_type if upload else None) or "audio/webm"
    if not audio:  # the no-mic "demo" button posts an empty clip — simulate it, store nothing
        return Recording(await _demo_stt.transcribe(audio, mime_type, hint=hint), None)
    # Upload while the STT works, so storage adds no wait for the child. `save` never raises.
    transcript, stored = await asyncio.gather(
        stt.transcribe(audio, mime_type, hint=hint),
        store.save(audio, mime_type, activity=activity, student_id=student_id),
    )
    return Recording(transcript, stored.uri if stored else None)
