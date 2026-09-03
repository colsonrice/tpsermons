"""Boundary types.

`Guide` is the contract between `generate` and `render`. Metadata fields are
injected by code; only the prose fields are model-authored, which is what makes
hallucinated links structurally impossible.
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

RECAP_WORDS = (60, 150)
ACTION_WORDS = (40, 120)
DISCUSS_BLOCKS = 3
QUESTIONS_PER_BLOCK = (2, 3)
REFLECTIONS = 3


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
    questions: List[str]


@dataclass
class Guide:
    title: str
    series: Optional[str]
    speaker: Optional[str]
    date: str
    passage: Optional[str]
    links: Dict[str, str]
    recap: str
    discuss: List[DiscussBlock]
    take_action: str
    reflections: List[str]
    source: str = ""

    def validate(self) -> "Guide":
        if "tpcc" not in self.links or not self.links["tpcc"]:
            raise ValidationError("links.tpcc is required and is never omitted")

        _words("recap", self.recap, *RECAP_WORDS)
        _words("take_action", self.take_action, *ACTION_WORDS)

        if len(self.discuss) != DISCUSS_BLOCKS:
            raise ValidationError(
                "expected %d discuss blocks, got %d" % (DISCUSS_BLOCKS, len(self.discuss)))
        lo, hi = QUESTIONS_PER_BLOCK
        for i, b in enumerate(self.discuss):
            if not b.heading.strip():
                raise ValidationError("discuss[%d] has an empty heading" % i)
            if not lo <= len(b.questions) <= hi:
                raise ValidationError(
                    "discuss[%d] has %d questions, expected %d-%d" % (i, len(b.questions), lo, hi))
            for q in b.questions:
                _placeholder("discuss[%d]" % i, q)

        if len(self.reflections) != REFLECTIONS:
            raise ValidationError(
                "expected %d reflections, got %d" % (REFLECTIONS, len(self.reflections)))
        for r in self.reflections:
            _placeholder("reflections", r)
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
