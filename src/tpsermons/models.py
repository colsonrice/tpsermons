"""Boundary types.

`Guide` is the contract between `generate` and `render`. Metadata fields are
injected by code; only the prose fields are model-authored, which is what makes
hallucinated links and invented speaker names structurally impossible rather
than merely unlikely.

The guide is shaped as a runnable 45-60 minute script for a men's group of
about twelve. The deep questions happen in groups of four, because discussion
participation collapses above six people and twelve men in one circle means
three or four carry the room.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

# Whole-token placeholders only. Bare "..." and bracketed ASR markers such as
# "[inaudible]" must NOT trip this -- ellipses occur in legitimate quotation.
_PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX|Lorem)\b", re.IGNORECASE)
_BRACKET_STUB = re.compile(r"\[insert[^\]]*\]", re.IGNORECASE)

DISCUSS_BLOCKS = 3
PROBES_PER_BLOCK = (2, 3)
LEADER_NOTES = (2, 4)
CONTEXT_WORDS = (12, 70)
COMMIT_WORDS = (15, 90)

# The evening, as minutes. Sums to 55 -- inside the 45-60 window.
SEGMENTS = (
    ("Open", 5, "all together"),
    ("Read", 8, "all together"),
    ("Dig in", 27, "groups of four"),
    ("Regroup", 10, "all together"),
    ("Commit", 5, "all together"),
)


class ValidationError(Exception):
    """Raised when model output does not conform to the Guide shape."""


@dataclass(frozen=True)
class Episode:
    guid: str
    title: str
    pub_date: datetime
    mp3_url: str
    series: Optional[str] = None
    passage: Optional[str] = None
    raw_title: str = ""

    @property
    def slug(self) -> str:
        s = re.sub(r"[^a-z0-9]+", "-", self.title.lower()).strip("-")
        return s or "message"


@dataclass(frozen=True)
class SourcedText:
    text: str
    source: str  # transcript_pdf | youtube_captions | whisper


@dataclass(frozen=True)
class DiscussBlock:
    heading: str
    question: str
    probes: List[str]


@dataclass
class Guide:
    # --- injected by code -------------------------------------------------
    title: str
    series: Optional[str]
    speaker: Optional[str]
    date: str
    passage: Optional[str]
    links: Dict[str, str]
    # --- authored by the model -------------------------------------------
    leader_notes: List[str]
    opener: str
    context: str
    read_aloud: str
    observation: str
    discuss: List[DiscussBlock]
    obstacle: str
    commit: str
    carry: str
    source: str = ""

    def validate(self) -> "Guide":
        if "tpcc" not in self.links or not self.links["tpcc"]:
            raise ValidationError("links.tpcc is required and is never omitted")

        lo, hi = LEADER_NOTES
        if not lo <= len(self.leader_notes) <= hi:
            raise ValidationError(
                "expected %d-%d leader notes, got %d" % (lo, hi, len(self.leader_notes)))
        for n in self.leader_notes:
            _placeholder("leader_notes", n)

        for name in ("opener", "read_aloud", "observation", "obstacle", "carry"):
            _placeholder(name, getattr(self, name))
        _words("context", self.context, *CONTEXT_WORDS)
        _words("commit", self.commit, *COMMIT_WORDS)

        for name in ("opener", "observation", "obstacle"):
            if "?" not in getattr(self, name):
                raise ValidationError("%s must be a question" % name)

        if len(self.discuss) != DISCUSS_BLOCKS:
            raise ValidationError(
                "expected %d discuss blocks, got %d" % (DISCUSS_BLOCKS, len(self.discuss)))
        plo, phi = PROBES_PER_BLOCK
        for i, b in enumerate(self.discuss):
            if not b.heading.strip():
                raise ValidationError("discuss[%d] has an empty heading" % i)
            _placeholder("discuss[%d].question" % i, b.question)
            if "?" not in b.question:
                raise ValidationError("discuss[%d].question must be a question" % i)
            if not plo <= len(b.probes) <= phi:
                raise ValidationError(
                    "discuss[%d] has %d probes, expected %d-%d" % (i, len(b.probes), plo, phi))
            for p in b.probes:
                _placeholder("discuss[%d].probes" % i, p)
        return self


def _words(name: str, value: str, lo: int, hi: int) -> None:
    _placeholder(name, value)
    n = len(value.split())
    if not lo <= n <= hi:
        raise ValidationError("%s is %d words, expected %d-%d" % (name, n, lo, hi))


def _placeholder(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValidationError("%s is empty" % name)
    m = _PLACEHOLDER.search(value) or _BRACKET_STUB.search(value)
    if m:
        raise ValidationError("%s contains placeholder text: %r" % (name, m.group(0)))
