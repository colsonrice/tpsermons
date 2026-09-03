"""Title parsing and sermon detection.

TPCC titles a sermon `Title | Series | Passage`. That three-segment shape is
load-bearing twice: it yields the passage used to anchor the model against ASR
citation errors, and it distinguishes a sermon from the short clips and podcast
episodes the same feeds carry.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

FULL_GATHERING = "full gathering"
_WS = re.compile(r"\s+")


@dataclass(frozen=True)
class ParsedTitle:
    title: str
    series: Optional[str] = None
    passage: Optional[str] = None


def normalize(raw: str) -> str:
    """Collapse whitespace and casefold, for exact cross-source title matching."""
    return _WS.sub(" ", raw).strip().casefold()


def segments(raw: str) -> List[str]:
    return [s.strip() for s in raw.split("|") if s.strip()]


def parse_title(raw: str) -> ParsedTitle:
    """Split a title. Unparseable titles yield None fields rather than raising."""
    segs = segments(raw)
    if len(segs) == 3:
        return ParsedTitle(segs[0], segs[1], segs[2])
    return ParsedTitle(segs[0] if segs else _WS.sub(" ", raw).strip())


def is_sermon_title(raw: str) -> bool:
    """True only for the message-only cut of a sermon.

    Rejects clips (no pipe structure), podcast episodes (two segments), and the
    Full Gathering cut (four segments, worship and announcements included).
    """
    segs = segments(raw)
    if len(segs) != 3:
        return False
    return segs[-1].casefold() != FULL_GATHERING
