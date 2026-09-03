"""Paid fallback: transcribe the podcast MP3 when free sources are unavailable.

Re-encoding to 16 kHz mono 32 kbps puts even the longest observed sermon
(68.5 min) at ~16.4 MB, under the 25 MB upload cap, so each sermon is a single
API call with no chunking.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import List

PRIMARY_MODEL = "gpt-4o-mini-transcribe"
RETRY_MODEL = "whisper-1"


def ffmpeg_args(src: str, dst: str) -> List[str]:
    return ["ffmpeg", "-y", "-i", src, "-ac", "1", "-ar", "16000", "-b:a", "32k", dst]


def downsample(src: Path, dst: Path) -> Path:
    subprocess.run(ffmpeg_args(str(src), str(dst)), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dst


def transcribe_file(path: Path, client) -> str:
    """Transcribe, retrying once against a different model."""
    last = None
    for model in (PRIMARY_MODEL, RETRY_MODEL):
        try:
            with open(path, "rb") as fh:
                return client.audio.transcriptions.create(
                    model=model, file=fh, response_format="text")
        except Exception as exc:  # pragma: no cover - network path
            last = exc
    raise RuntimeError("transcription failed: %s" % last)


def transcribe_url(mp3_url: str, client, fetch) -> str:  # pragma: no cover - network path
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.mp3"
        small = Path(tmp) / "small.mp3"
        raw.write_bytes(fetch(mp3_url))
        downsample(raw, small)
        return transcribe_file(small, client)
