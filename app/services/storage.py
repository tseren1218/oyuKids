"""Recording storage: every attempt's audio goes to S3 as WAV, for the lakehouse / oyuLLM training.

Objects are laid out Hive-style so lakehouse engines can prune by partition:

    s3://<bucket>/recordings/activity=reading/date=2026-10-16/student=12/<uuid>.wav

Requests are signed with AWS Signature V4 directly over httpx (no boto3 dependency).
"""

import asyncio
import hashlib
import hmac
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Protocol
from urllib.parse import quote

import httpx

from app.config import Settings

log = logging.getLogger("oyukids.storage")

RECORDINGS_PREFIX = "recordings"


@dataclass
class StoredAudio:
    uri: str  # s3://bucket/key — what we persist
    key: str
    size: int
    content_type: str


def is_wav(data: bytes) -> bool:
    return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def recording_key(activity: str, student_id: int, ext: str, today: date | None = None) -> str:
    day = (today or date.today()).isoformat()
    return f"{RECORDINGS_PREFIX}/activity={activity}/date={day}/student={student_id}/{uuid.uuid4().hex}.{ext}"


class AudioStore(Protocol):
    async def save(self, audio: bytes, content_type: str, *, activity: str, student_id: int) -> StoredAudio | None: ...
    def playback_url(self, uri: str, expires: int = 900) -> str | None: ...


class NullAudioStore:
    """Used when S3 isn't configured (and in tests): nothing is stored."""

    async def save(self, audio, content_type, *, activity, student_id):
        return None

    def playback_url(self, uri, expires=900):
        return None


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


class S3AudioStore:
    ATTEMPTS = 3  # network errors only; runs concurrently with STT so retries rarely add wait
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str, timeout: float = 60, host: str | None = None):
        self.bucket, self.region = bucket, region
        self.access_key, self.secret_key = access_key, secret_key
        self.host = host or f"{bucket}.s3.{region}.amazonaws.com"  # virtual-hosted, regional endpoint
        self.timeout = timeout

    # ── SigV4 ────────────────────────────────────────────────────────────────
    def _signing_key(self, datestamp: str) -> bytes:
        key = _hmac(f"AWS4{self.secret_key}".encode(), datestamp)
        for part in (self.region, "s3", "aws4_request"):
            key = _hmac(key, part)
        return key

    def _signature(self, amz_date: str, canonical_request: str) -> tuple[str, str]:
        scope = f"{amz_date[:8]}/{self.region}/s3/aws4_request"
        to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest()])
        return scope, hmac.new(self._signing_key(amz_date[:8]), to_sign.encode(), hashlib.sha256).hexdigest()

    def _signed_headers(self, method: str, key: str, payload: bytes, extra: dict[str, str]) -> dict[str, str]:
        amz_date = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        payload_hash = hashlib.sha256(payload).hexdigest()
        headers = {"host": self.host, "x-amz-content-sha256": payload_hash, "x-amz-date": amz_date, **{k.lower(): v for k, v in extra.items()}}
        names = sorted(headers)
        canonical = "\n".join([
            method, "/" + quote(key, safe="/-_.~"), "",
            "".join(f"{n}:{headers[n].strip()}\n" for n in names), ";".join(names), payload_hash,
        ])
        scope, signature = self._signature(amz_date, canonical)
        headers["authorization"] = (f"AWS4-HMAC-SHA256 Credential={self.access_key}/{scope}, "
                                    f"SignedHeaders={';'.join(names)}, Signature={signature}")
        del headers["host"]
        return headers

    def _request(self, method: str, key: str, payload: bytes = b"", extra: dict[str, str] | None = None) -> httpx.Request:
        url = f"https://{self.host}/" + quote(key, safe="/-_.~")
        return httpx.Request(method, url, content=payload, headers=self._signed_headers(method, key, payload, extra or {}))

    # ── API ──────────────────────────────────────────────────────────────────
    async def put(self, key: str, data: bytes, content_type: str) -> None:
        request = self._request("PUT", key, data, {"content-type": content_type, "x-amz-server-side-encryption": "AES256"})
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.send(request)
        if res.status_code != 200:
            raise RuntimeError(f"S3 PUT {res.status_code}: {res.text[:300]}")

    async def delete(self, key: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.send(self._request("DELETE", key))
        if res.status_code not in (200, 204):
            raise RuntimeError(f"S3 DELETE {res.status_code}: {res.text[:300]}")

    def presigned_get(self, key: str, expires: int = 900, now: datetime | None = None) -> str:
        amz_date = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
        scope = f"{amz_date[:8]}/{self.region}/s3/aws4_request"
        query = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key}/{scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(expires),
            "X-Amz-SignedHeaders": "host",
        }
        canonical_query = "&".join(f"{quote(k, safe='-_.~')}={quote(v, safe='-_.~')}" for k, v in sorted(query.items()))
        path = "/" + quote(key, safe="/-_.~")
        canonical = "\n".join(["GET", path, canonical_query, f"host:{self.host}\n", "host", "UNSIGNED-PAYLOAD"])
        _, signature = self._signature(amz_date, canonical)
        return f"https://{self.host}{path}?{canonical_query}&X-Amz-Signature={signature}"

    def key_from_uri(self, uri: str) -> str | None:
        prefix = f"s3://{self.bucket}/"
        return uri[len(prefix):] if uri and uri.startswith(prefix) else None

    async def save(self, audio: bytes, content_type: str, *, activity: str, student_id: int) -> StoredAudio | None:
        """Upload a recording. Never raises: a storage hiccup must not cost a child their result."""
        if not audio:
            return None
        wav = is_wav(audio)
        ext = "wav" if wav else {"audio/webm": "webm", "audio/mp4": "m4a", "audio/ogg": "ogg"}.get(content_type.split(";")[0], "bin")
        key = recording_key(activity, student_id, ext)
        for attempt in range(1, self.ATTEMPTS + 1):
            try:
                await self.put(key, audio, "audio/wav" if wav else content_type.split(";")[0])
                break
            except httpx.HTTPError as exc:  # DNS / connect / timeout — worth retrying
                if attempt == self.ATTEMPTS:
                    log.error("recording upload failed after %d tries (%s): %r", attempt, key, exc)
                    return None
                await asyncio.sleep(attempt)
            except Exception:  # S3 said no (e.g. AccessDenied) — retrying won't help
                log.exception("recording upload rejected (%s, %d bytes)", key, len(audio))
                return None
        return StoredAudio(f"s3://{self.bucket}/{key}", key, len(audio), "audio/wav" if wav else content_type)

    def playback_url(self, uri: str, expires: int = 900) -> str | None:
        key = self.key_from_uri(uri)
        return self.presigned_get(key, expires) if key else None


def build_audio_store(settings: Settings) -> AudioStore:
    if settings.s3_bucket_name and settings.aws_access_key_id and settings.aws_secret_access_key:
        return S3AudioStore(settings.s3_bucket_name, settings.aws_region, settings.aws_access_key_id, settings.aws_secret_access_key)
    return NullAudioStore()
