import asyncio
import re
import struct
from datetime import datetime, timezone

from app.deps import get_audio_store, get_stt
from app.main import app
from app.services.storage import NullAudioStore, S3AudioStore, StoredAudio, is_wav, recording_key


def wav_bytes(seconds: float = 0.1, rate: int = 16000) -> bytes:
    n = int(seconds * rate)
    return b"RIFF" + struct.pack("<I", 36 + n * 2) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) \
        + b"data" + struct.pack("<I", n * 2) + b"\x00\x00" * n


class FakeStore(NullAudioStore):
    def __init__(self, fail: bool = False):
        self.saved, self.fail = [], fail

    async def save(self, audio, content_type, *, activity, student_id):
        if self.fail:
            return None  # S3AudioStore.save swallows errors and returns None
        self.saved.append((len(audio), content_type, activity, student_id))
        return StoredAudio(f"s3://bucket/recordings/activity={activity}/x.wav", "k", len(audio), content_type)


class EchoSTT:
    async def transcribe(self, audio, mime_type, *, hint=None):
        from app.services.stt import Transcript
        return Transcript(text=hint or "", provider="echo", duration_seconds=10.0)


def test_aws_documented_presigned_url_example():
    # AWS docs, "Authenticating Requests: Using Query Parameters (AWS Signature Version 4)" example.
    store = S3AudioStore("examplebucket", "us-east-1", "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                         host="examplebucket.s3.amazonaws.com")  # the docs use the global endpoint
    url = store.presigned_get("test.txt", expires=86400, now=datetime(2013, 5, 24, tzinfo=timezone.utc))
    assert url.endswith("X-Amz-Signature=aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404")


def test_key_layout_is_hive_partitioned():
    key = recording_key("reading", 12, "wav")
    assert re.fullmatch(r"recordings/activity=reading/date=\d{4}-\d{2}-\d{2}/student=12/[0-9a-f]{32}\.wav", key)
    assert is_wav(wav_bytes()) and not is_wav(b"\x1aE\xdf\xa3 webm")


def test_recording_is_stored_and_url_saved(student):
    store = FakeStore()
    app.dependency_overrides.update({get_audio_store: lambda: store, get_stt: EchoSTT})
    try:
        res = student.post("/reading/1/attempts", data={"duration_ms": "10000"}, files={"audio": ("r.wav", wav_bytes(), "audio/wav")})
        assert res.status_code == 200
        assert store.saved == [(len(wav_bytes()), "audio/wav", "reading", 1)]
        from app.deps import get_repo
        latest = get_repo().list_attempts(student_ids=[1], limit=1)[0]
        assert latest.audio_url == "s3://bucket/recordings/activity=reading/x.wav"
    finally:
        app.dependency_overrides.clear()


def test_demo_clip_uploads_nothing(student):
    store = FakeStore()
    app.dependency_overrides[get_audio_store] = lambda: store
    try:
        student.post("/poems/1/attempts", data={"duration_ms": "9000"}, files={"audio": ("a.webm", b"", "audio/webm")})
        assert store.saved == []
    finally:
        app.dependency_overrides.clear()


def test_storage_failure_does_not_cost_the_result(student):
    app.dependency_overrides.update({get_audio_store: lambda: FakeStore(fail=True), get_stt: EchoSTT})
    try:
        res = student.post("/reading/1/attempts", data={"duration_ms": "10000"}, files={"audio": ("r.wav", wav_bytes(), "audio/wav")})
        assert res.status_code == 200 and "үг/мин" in res.text
        from app.deps import get_repo
        assert get_repo().list_attempts(student_ids=[1], limit=1)[0].audio_url is None
    finally:
        app.dependency_overrides.clear()


def test_s3_save_never_raises(monkeypatch):
    store = S3AudioStore("b", "ap-southeast-1", "AKIA", "secret")

    async def boom(*a, **k):
        raise RuntimeError("S3 PUT 403")

    monkeypatch.setattr(store, "put", boom)
    assert asyncio.run(store.save(wav_bytes(), "audio/wav", activity="reading", student_id=1)) is None


def test_teacher_playback_is_presigned_and_scoped(teacher, login):
    from app.deps import get_repo
    attempt = get_repo().list_attempts(student_ids=[1], limit=1)[0]
    attempt.audio_url = "s3://oyu-kids-bucket/recordings/activity=reading/date=2026-10-16/student=1/abc.wav"
    s3 = S3AudioStore("oyu-kids-bucket", "ap-southeast-1", "AKIATEST", "secret")
    app.dependency_overrides[get_audio_store] = lambda: s3
    try:
        res = teacher.get(f"/teacher/attempts/{attempt.id}/audio", follow_redirects=False)
        assert res.status_code == 307
        loc = res.headers["location"]
        assert loc.startswith("https://oyu-kids-bucket.s3.ap-southeast-1.amazonaws.com/recordings/activity%3Dreading/")
        assert "X-Amz-Signature=" in loc and "X-Amz-Expires=900" in loc
        other = login("bat", "teacher")  # Номин isn't in any of Бат багш's classes
        assert other.get(f"/teacher/attempts/{attempt.id}/audio", follow_redirects=False).status_code == 404
        kid = login("nomin", "student")
        assert kid.get(f"/teacher/attempts/{attempt.id}/audio", follow_redirects=False).status_code == 303
    finally:
        app.dependency_overrides.clear()


def test_s3_save_retries_network_errors(monkeypatch):
    import httpx
    store = S3AudioStore("b", "ap-southeast-1", "AKIA", "secret")
    calls = []

    async def flaky(*a, **k):
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ConnectError("nodename nor servname provided")

    async def no_sleep(_):
        pass

    monkeypatch.setattr(store, "put", flaky)
    monkeypatch.setattr("app.services.storage.asyncio.sleep", no_sleep)
    stored = asyncio.run(store.save(wav_bytes(), "audio/wav", activity="words", student_id=3))
    assert len(calls) == 3 and stored.uri.startswith("s3://b/recordings/activity=words/") and stored.uri.endswith(".wav")
