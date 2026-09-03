"""Captivate podcast feed parsing.

The podcast feed is the discovery source: it is authoritative, complete
(224 episodes), and unlike YouTube it is not subject to bot-blocking. It also
carries the MP3 that backs the Whisper fallback.

Pure: takes XML text, returns Episodes. No network.
"""
from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import List, Optional

from .models import Episode
from .titles import is_sermon_title, parse_title


def _text(item: ET.Element, tag: str) -> Optional[str]:
    el = item.find(tag)
    if el is None or el.text is None:
        return None
    return el.text.strip()


def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_feed(xml_text: str) -> List[Episode]:
    """Parse the feed into sermon Episodes, newest first.

    Items whose titles lack the three-segment sermon structure -- clips and
    podcast episodes -- are skipped entirely.
    """
    root = ET.fromstring(xml_text)
    episodes = []
    for item in root.iter("item"):
        raw_title = _text(item, "title")
        if not raw_title or not is_sermon_title(raw_title):
            continue

        enclosure = item.find("enclosure")
        mp3_url = enclosure.get("url") if enclosure is not None else None
        guid = _text(item, "guid")
        pub_date = _parse_date(_text(item, "pubDate"))
        if not (mp3_url and guid and pub_date):
            continue

        parsed = parse_title(raw_title)
        episodes.append(Episode(
            guid=guid,
            title=parsed.title,
            pub_date=pub_date,
            mp3_url=mp3_url,
            series=parsed.series,
            passage=parsed.passage,
            raw_title=raw_title,
        ))

    episodes.sort(key=lambda e: e.pub_date, reverse=True)
    return episodes
