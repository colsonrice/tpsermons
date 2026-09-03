"""YouTube caption retrieval.

Captions are the primary text source: free, same-day, and measured within 1.7%
of TPCC's own transcript. Retrieval uses youtube-transcript-api -- fetching the
signed /api/timedtext URL directly returns 200 with a zero-byte body, so the
library's InnerTube path is what actually works.

The video id comes from the TPCC message page, not YouTube's channel feed --
that feed began returning 404/500 under repeated access from a residential IP
during development, while TPCC's own server does not throttle.

Normalization is pure; only `fetch_captions` touches the network.
"""
from __future__ import annotations

import re
from typing import Optional, Sequence

# ASR emits bracketed non-speech markers. Measured on a full sermon: only 8 of
# them ([music] x6, [applause], [laughter]). Strip them; keep everything else.
_MARKER = re.compile(r"\[[^\]]{1,30}\]")
_WS = re.compile(r"\s+")


def normalize_cues(cues: Sequence[str]) -> str:
    """Join caption cues into clean prose.

    Measured on a real sermon: cues are discrete with zero rolling duplicates
    and no embedded newlines, so joining is all that is required beyond marker
    stripping and whitespace collapse.
    """
    joined = " ".join(c for c in cues if c)
    joined = _MARKER.sub(" ", joined)
    return _WS.sub(" ", joined).strip()


def fetch_captions(video_id: str) -> Optional[str]:
    """Fetch and normalize English captions. Returns None on any failure.

    Failure is expected and non-fatal: YouTube rate-limits datacenter ranges,
    so a blocked run simply falls through to the Whisper branch.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        fetched = YouTubeTranscriptApi().fetch(video_id)
        return normalize_cues([snippet.text for snippet in fetched])
    except Exception:
        return None
