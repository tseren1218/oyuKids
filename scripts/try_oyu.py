"""Smoke-test the oyu speech API against oyuKids content.

Round trip: tsuurAI (TTS) speaks our seed texts → Anir (STT) transcribes them → our scorer
compares. Extra audio files given on the command line are transcribed as-is.

    OYU_STT_API_KEY=... python -m scripts.try_oyu [--model v4] [--out DIR] [file ...]
"""

import argparse
import asyncio
import time
from pathlib import Path

import httpx

from app.config import get_settings
from app.db import seed
from app.services.scoring import align
from app.services.stt import OyuSTT

SAMPLES = [
    ("passage", seed.PASSAGES[0].body),
    ("quote", seed.PASSAGES[4].body),
    ("poem", seed.POEMS[0].body.replace("\n", ". ")),
    ("words", ", ".join(seed.COMPOUND_WORDS[:6])),
]
MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".webm": "audio/webm", ".m4a": "audio/mp4", ".mp4": "audio/mp4"}


async def synthesize(client: httpx.AsyncClient, base: str, key: str, text: str, voice: str) -> bytes:
    res = await client.post(f"{base}/v1/audio/speech", headers={"Authorization": f"Bearer {key}"}, json={"text": text, "voice": voice})
    res.raise_for_status()
    return res.content


async def transcribe(stt: OyuSTT, label: str, audio: bytes, mime: str, reference: str | None) -> None:
    start = time.perf_counter()
    try:
        result = await stt.transcribe(audio, mime)
    except Exception as exc:  # report and keep going
        print(f"  ✗ {label:<22} {mime:<11} {exc}")
        return
    took = time.perf_counter() - start
    line = f"  ✓ {label:<22} {mime:<11} {took:5.1f}s  «{result.text}»"
    if reference:
        a = align(reference, result.text)
        line += f"\n    accuracy {a.accuracy:.0%} ({a.correct}/{a.total}, close {a.count('close')}, wrong {a.count('wrong')}, missed {a.count('missed')})"
    print(line)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None)
    parser.add_argument("--out", default="tts_samples")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()

    settings = get_settings()
    stt = OyuSTT(settings.oyu_api_url, settings.stt_api_key, args.model or settings.stt_model)
    out = Path(args.out)
    out.mkdir(exist_ok=True)

    async with httpx.AsyncClient(timeout=60) as client:
        print("TTS → STT round trip")
        for name, text in SAMPLES:
            for voice in ("female", "mbspeech"):
                path = out / f"{name}_{voice}.wav"
                if not path.exists():
                    path.write_bytes(await synthesize(client, settings.oyu_api_url, settings.stt_api_key, text, voice))
                await transcribe(stt, f"{name}/{voice}", path.read_bytes(), "audio/wav", text)

    if args.files:
        print("Your files")
        for f in map(Path, args.files):
            await transcribe(stt, f.name, f.read_bytes(), MIME.get(f.suffix.lower(), "application/octet-stream"), None)


if __name__ == "__main__":
    asyncio.run(main())
