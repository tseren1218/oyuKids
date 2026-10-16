"""Speech-to-text providers.

Every activity sends the child's recording through `STTProvider.transcribe`. The mock
fakes a transcript from the expected text (`hint`) so the full flow works without a
real API or even a microphone. Plug the real API into `HttpSTT` later.
"""

import random
from dataclasses import dataclass
from typing import Protocol

from fastapi import UploadFile

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


class HttpSTT:
    """Placeholder for the real STT API (credentials come via OYU_STT_* env vars)."""

    def __init__(self, url: str | None, api_key: str | None, language: str):
        self.url, self.api_key, self.language = url, api_key, language

    async def transcribe(self, audio: bytes, mime_type: str, *, hint: str | None = None) -> Transcript:
        # TODO: POST `audio` to self.url (httpx.AsyncClient) and map the response to Transcript.
        raise NotImplementedError("Real STT provider is not wired up yet — set OYU_STT_PROVIDER=mock")


def build_stt(settings: Settings) -> STTProvider:
    if settings.stt_provider == "http":
        return HttpSTT(settings.stt_api_url, settings.stt_api_key, settings.stt_language)
    return MockSTT()


async def transcribe_upload(stt: STTProvider, upload: UploadFile | None, *, hint: str | None = None) -> Transcript:
    audio = await upload.read() if upload else b""
    mime_type = (upload.content_type if upload else None) or "audio/webm"
    return await stt.transcribe(audio, mime_type, hint=hint)
