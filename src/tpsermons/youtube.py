"""YouTube video resolution and caption retrieval.

Captions are the primary text source: free, same-day, and measured within 1.7%
of TPCC's own transcript. Retrieval uses youtube-transcript-api -- fetching the
signed /api/timedtext URL directly returns 200 with a zero-byte body, so the
library's InnerTube path is what actually works.

Parsing and normalization are pure; only `fetch_captions` touches the network.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Sequence

from .titles import is_sermon_title, normalize

CHANNEL_ID = "UCYlj586dgrLdWZhD_znqQhg"
CHANNEL_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=%s" % CHANNEL_ID

_NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
       "media": "http://search.yahoo.com/mrss/"}

# ASR emits bracketed non-speech markers. Measured on a full sermon: only 8 of
# them ([music] x6, [applause], [laughter]). Strip them; keep everything else.
_MARKER = re.compile(r"\[[^\]]{1,30}\]")
_WS = re.compile(r"\s+")


def find_video(channel_xml: str, sermon_title: str) -> Optional[str]:
    """Return the video id of the message-only cut, or None.

    The message-only title is byte-identical to the podcast title; the Full
    Gathering cut appends a suffix and so loses the exact match automatically.
    The is_sermon_title guard is belt-and-braces on top of that.
    """
    want = normalize(sermon_title)
    root = ET.fromstring(channel_xml)
    for entry in root.findall("a:entry", _NS):
        title_el = entry.find("a:title", _NS)
        vid_el = entry.find("yt:videoId", _NS)
        if title_el is None or vid_el is None or not title_el.text:
            continue
        candidate = title_el.text
        if not is_sermon_title(candidate):
            continue
        if normalize(candidate) == want:
            return vid_el.text
    return None


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
