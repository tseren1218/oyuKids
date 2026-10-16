import asyncio

import httpx
import pytest

from app.deps import get_stt
from app.main import app
from app.services import stt as stt_module
from app.services.stt import OyuSTT, STTError, Transcript


class FailingSTT:
    async def transcribe(self, audio, mime_type, *, hint=None) -> Transcript:
        raise STTError("boom")


@pytest.fixture
def oyu_responds(monkeypatch):
    """Route OyuSTT's httpx calls to a fake handler; returns the list of captured requests."""
    seen: list[httpx.Request] = []

    def install(status: int, body: dict):
        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(status, json=body)

        real = httpx.AsyncClient
        monkeypatch.setattr(stt_module.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
        return seen

    return install


def test_oyu_parses_text_and_duration(oyu_responds):
    seen = oyu_responds(200, {"text": " сайн байна уу ", "duration_s": 2.5, "capability": "auto"})
    result = asyncio.run(OyuSTT("https://api.oyu.so", "sk-test").transcribe(b"RIFF....", "audio/webm;codecs=opus"))
    assert (result.text, result.duration_seconds, result.provider) == ("сайн байна уу", 2.5, "oyu")
    req = seen[0]
    assert str(req.url) == "https://api.oyu.so/v1/audio/transcriptions"
    assert req.headers["authorization"] == "Bearer sk-test"
    assert b'filename="audio.webm"' in req.content and b"Content-Type: audio/webm" in req.content


def test_oyu_error_status_raises(oyu_responds):
    oyu_responds(400, {"detail": "could not decode audio"})
    with pytest.raises(STTError, match="400"):
        asyncio.run(OyuSTT("https://api.oyu.so", "sk-test").transcribe(b"junk", "audio/webm"))


def test_oyu_requires_key():
    with pytest.raises(STTError):
        OyuSTT("https://api.oyu.so", None)


def test_demo_clip_bypasses_real_stt_and_failures_return_502(student):
    app.dependency_overrides[get_stt] = FailingSTT
    try:
        client = student
        demo = client.post("/reading/1/attempts", data={"duration_ms": "20000"}, files={"audio": ("a.webm", b"", "audio/webm")})
        assert demo.status_code == 200 and "(mock)" in demo.text
        real = client.post("/reading/1/attempts", data={"duration_ms": "20000"}, files={"audio": ("a.webm", b"\x1aE\xdf\xa3", "audio/webm")})
        assert real.status_code == 502
    finally:
        app.dependency_overrides.clear()
