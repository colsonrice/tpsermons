"""TPCC message-page and series-page parsing.

The church's own server is the sturdiest link in the chain: it carries the
message-only video id, the transcript PDF once posted, and the speaker. Unlike
YouTube's channel feed it does not throttle, so video-id resolution goes
through here rather than through YouTube.

Message slugs must be *looked up*, never derived. Real counter-examples:
"Enough" -> enough-1, and "Why You're Exhausted..." -> rest-killers, which
shares no words with its title.

Pure: every function takes markup text. Network access lives in cli/source.
"""
from __future__ import annotations

import html
import re
from typing import Dict, Optional

BASE = "https://tpcc.org"

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_DATE_PREFIX = re.compile(r"^\d{1,2}\.\d{1,2}\s*/\s*")

_MESSAGE_HREF = re.compile(r'<a[^>]*href="(/messages/([a-z0-9][a-z0-9\-]*))"[^>]*>(.*?)</a>',
                           re.S | re.I)
_VIDEO_ID = re.compile(r'(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([A-Za-z0-9_-]{11})')
_FIRST_P = re.compile(r"<p[^>]*>(.*?)</p>", re.S | re.I)
_TRANSCRIPT = re.compile(r'Transcript:\s*<a[^>]*href="([^"]+)"', re.I)
_SPEAKER = re.compile(
    r'In this message,\s*(?:[A-Z][A-Za-z\'\-]*\s+){0,4}?'
    r'(?:Pastor|Minister|Director)\s+([A-Z][A-Za-z\'\-]+(?:\s+[A-Z][A-Za-z\'\-]+){1,2})'
    r'\s+(?:teaches|preaches|shares|walks|unpacks|explains)',
)


def _strip(markup: str) -> str:
    return _WS.sub(" ", html.unescape(_TAGS.sub(" ", markup))).strip()


def series_slug(series: str) -> str:
    """`The Urgent Kingdom` -> `the-urgent-kingdom`."""
    return re.sub(r"[^a-z0-9]+", "-", series.lower()).strip("-")


def series_url(series: str) -> str:
    return "%s/message-series/%s" % (BASE, series_slug(series))


def message_url(slug: str) -> str:
    return "%s/messages/%s" % (BASE, slug)


def parse_series_page(html_text: str) -> Dict[str, str]:
    """Map normalized message title -> slug.

    The title lives in the anchor's first <p> as `MM.DD / Title`; the
    description follows in a separate <p>. Taking only the first paragraph is
    what keeps the description out of the key.
    """
    mapping = {}
    for _href, slug, inner in _MESSAGE_HREF.findall(html_text):
        first_p = _FIRST_P.search(inner)
        if not first_p:
            continue
        title = _DATE_PREFIX.sub("", _strip(first_p.group(1)))
        key = _title_key(title)
        if key and key not in mapping:
            mapping[key] = slug
    return mapping


def _title_key(title: str) -> str:
    return _WS.sub(" ", re.sub(r"[^a-z0-9 ]+", "", title.lower())).strip()


def lookup_slug(html_text: str, title: str) -> Optional[str]:
    """Find the message slug for an episode title, or None."""
    mapping = parse_series_page(html_text)
    want = _title_key(title)
    if want in mapping:
        return mapping[want]
    for key, slug in mapping.items():
        if key.startswith(want) or want.startswith(key):
            return slug
    return None


def find_video_id(html_text: str) -> Optional[str]:
    """The embedded message-only video id, or None."""
    m = _VIDEO_ID.search(html_text)
    return m.group(1) if m else None


def find_transcript_url(html_text: str) -> Optional[str]:
    """Absolute URL of the official transcript PDF, or None if not yet posted."""
    m = _TRANSCRIPT.search(html_text)
    if not m:
        return None
    href = html.unescape(m.group(1))
    return href if href.startswith("http") else BASE + href


def find_speaker(html_text: str) -> Optional[str]:
    """Best-effort speaker name. Never fatal -- the header simply omits it."""
    m = _SPEAKER.search(_strip(html_text))
    return m.group(1).strip() if m else None
