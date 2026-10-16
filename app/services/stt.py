"""Speech-to-text providers.

Every activity sends the child's recording through `STTProvider.transcribe`. The mock
fakes a transcript from the expected text (`hint`) so the full flow works without a
real API or even a microphone. Plug the real API into `HttpSTT` later.
"""

import random
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings


@dataclass
class Transcript:
    text: str
    provider: str
    duration_seconds: float | None = None  # if the API reports audio length
    confidence: float | None = None


class STTProvider(Protocol):
    async def transcribe(self, audio: bytes, mime_type: str, *, hint: str | None = None) -> Transcript: ...


class MockSTT:
    """Pretends to be a child reading `hint` aloud: skips, mispronounces and mixes up a few words."""

    def __init__(
        self,
        skip_rate: float = 0.07,
        stumble_rate: float = 0.06,
        mixup_rate: float = 0.04,
        filler_rate: float = 0.03,
        seed: int | None = None,
    ):
        self.skip_rate = skip_rate
        self.stumble_rate = stumble_rate
        self.mixup_rate = mixup_rate
        self.filler_rate = filler_rate
        self._rng = random.Random(seed)

    async def transcribe(self, audio: bytes, mime_type: str, *, hint: str | None = None) -> Transcript:
        if not hint:
            return Transcript(text="", provider="mock", confidence=0.0)
        source = hint.split()
        words: list[str] = []
        for word in source:
            roll = self._rng.random()
            if roll < self.skip_rate:
                continue
            roll -= self.skip_rate
            if roll < self.stumble_rate and len(word) > 3:
                word = word[:-1]  # mispronounced ending — usually still a "close" match
            elif roll < self.stumble_rate + self.mixup_rate:
                word = self._rng.choice(source)  # said a different word
            words.append(word)
            if self._rng.random() < self.filler_rate:
                words.append("аан")
        return Transcript(text=" ".join(words), provider="mock", confidence=0.9)


class STTError(RuntimeError):
    pass


_EXTENSIONS = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/webm": "webm", "audio/mp4": "m4a"}


class OyuSTT:
    """Anir — oyu's Mongolian STT (https://dev.oyu.so). POST multipart `file` → {"text", "duration_s"}.

    Accepts wav/mp3/m4a/webm/ogg, so browser recordings go up as-is. `model` is sent if set but the
    API currently ignores it (always "auto").
    """

    def __init__(self, base_url: str, api_key: str | None, model: str | None = None, timeout: float = 60):
        if not api_key:
            raise STTError("OYU_STT_API_KEY is not set")
        self.url = base_url.rstrip("/") + "/v1/audio/transcriptions"
        self.api_key, self.model, self.timeout = api_key, model, timeout

    async def transcribe(self, audio: bytes, mime_type: str, *, hint: str | None = None) -> Transcript:
        if not audio:
            return Transcript(text="", provider="oyu")
        base_mime = mime_type.split(";")[0].strip()
        files = {"file": (f"audio.{_EXTENSIONS.get(base_mime, 'bin')}", audio, base_mime)}
        data = {"model": self.model} if self.model else {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(self.url, headers={"Authorization": f"Bearer {self.api_key}"}, files=files, data=data)
        except httpx.HTTPError as exc:
            raise STTError(f"oyu STT unreachable: {exc!r}") from exc
        if res.status_code != 200:
            raise STTError(f"oyu STT {res.status_code}: {res.text[:300]}")
        body = res.json()
        return Transcript(text=body.get("text", "").strip(), provider="oyu", duration_seconds=body.get("duration_s"))


def build_stt(settings: Settings) -> STTProvider:
    if settings.stt_provider == "oyu":
        return OyuSTT(settings.oyu_api_url, settings.stt_api_key, settings.stt_model)
    return MockSTT()

