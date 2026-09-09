"""Boundary types.

`Guide` is the contract between `generate` and `render`. Metadata is injected
by code; only the prose is model-authored, so hallucinated links and invented
speaker names are structurally impossible.

The shape follows the group's own written spec: a leader guide of roughly
three to four printed pages, plus a stripped-down participant reflection sheet
carrying the same questions in the first person.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

_PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX|Lorem)\b", re.IGNORECASE)
_BRACKET_STUB = re.compile(r"\[insert[^\]]*\]", re.IGNORECASE)
_EM_DASH = re.compile(r"[—–]")

# A question mark per prompt. A statement that sets up a single question is
# fine ("Think about a time when you were overlooked. What did you do?"), but
# two questions let a man answer the easier one and skip the other.
def _single_question(name: str, value: str) -> None:
    marks = value.count("?")
    if marks > 1:
        raise ValidationError(
            "%s asks %d questions in one prompt; split it or keep the sharper "
            "one (%r)" % (name, marks, value))
    # Zero question marks is fine: the spec endorses imperative prompts such
    # as "Think about a time when you were overlooked."

SECTIONS = (3, 4)            # 3 to 4 is the sweet spot; never more than 5
QUESTIONS_PER_SECTION = (2, 4)
TOTAL_QUESTIONS = (12, 15)   # 12 to 14 ideal for 60 minutes
ICEBREAKERS = 3              # labelled A / B / C
LEADER_NOTE_PARAS = (3, 5)
KEY_THEMES = (5, 7)
CHEAT_ROWS = (5, 7)


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
    source: str


@dataclass(frozen=True)
class Icebreaker:
    label: str          # A / B / C
    question: str
    fits: str           # which group dynamic this one suits


@dataclass(frozen=True)
class Section:
    title: str
    setup: str                        # 3-5 sentences grounding the section
    questions: List[str]              # 2-4, leader guide
    reflection_questions: List[str]   # same, rewritten first person


@dataclass(frozen=True)
class CheatRow:
    dynamic: str
    response: str


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
    goal: str
    leader_notes: List[str]
    scripture_instructions: str
    icebreakers: List[Icebreaker]
    sections: List[Section]
    closing_go_around: str
    prayer: str
    cheat_sheet: List[CheatRow]
    key_themes: List[str]
    commitment_prompt: str
    source: str = ""

    @property
    def question_count(self) -> int:
        return sum(len(s.questions) for s in self.sections)

    def validate(self) -> "Guide":
        if "tpcc" not in self.links or not self.links["tpcc"]:
            raise ValidationError("links.tpcc is required and is never omitted")

        _text("goal", self.goal)
        _text("scripture_instructions", self.scripture_instructions)
        _text("closing_go_around", self.closing_go_around)
        _text("prayer", self.prayer)
        _text("commitment_prompt", self.commitment_prompt)

        _count("leader_notes", self.leader_notes, *LEADER_NOTE_PARAS)
        for n in self.leader_notes:
            _text("leader_notes", n)

        if len(self.icebreakers) != ICEBREAKERS:
            raise ValidationError(
                "expected %d icebreakers, got %d" % (ICEBREAKERS, len(self.icebreakers)))
        for want, ice in zip("ABC", self.icebreakers):
            if ice.label.strip().upper() != want:
                raise ValidationError("icebreakers must be labelled A, B, C in order")
            _text("icebreaker %s" % want, ice.question)
            _single_question("icebreaker %s" % want, ice.question)
            _text("icebreaker %s fits" % want, ice.fits)

        _count("sections", self.sections, *SECTIONS)
        qlo, qhi = QUESTIONS_PER_SECTION
        for i, sec in enumerate(self.sections):
            _text("sections[%d].title" % i, sec.title)
            _text("sections[%d].setup" % i, sec.setup)
            _count("sections[%d].questions" % i, sec.questions, qlo, qhi)
            for q in sec.questions:
                _text("sections[%d].question" % i, q)
                _single_question("sections[%d].question" % i, q)
            if len(sec.reflection_questions) != len(sec.questions):
                raise ValidationError(
                    "sections[%d] has %d questions but %d reflection questions; "
                    "the sheet mirrors the guide"
                    % (i, len(sec.questions), len(sec.reflection_questions)))
            for q in sec.reflection_questions:
                _text("sections[%d].reflection" % i, q)
                _single_question("sections[%d].reflection" % i, q)

        tlo, thi = TOTAL_QUESTIONS
        if not tlo <= self.question_count <= thi:
            raise ValidationError(
                "expected %d-%d discussion questions in total, got %d"
                % (tlo, thi, self.question_count))

        _count("key_themes", self.key_themes, *KEY_THEMES)
        for t in self.key_themes:
            _text("key_themes", t)
        _count("cheat_sheet", self.cheat_sheet, *CHEAT_ROWS)
        for row in self.cheat_sheet:
            _text("cheat_sheet.dynamic", row.dynamic)
            _text("cheat_sheet.response", row.response)
        return self


def _count(name, items, lo, hi) -> None:
    if not lo <= len(items) <= hi:
        raise ValidationError("expected %d-%d %s, got %d" % (lo, hi, name, len(items)))


def _text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValidationError("%s is empty" % name)
    m = _PLACEHOLDER.search(value) or _BRACKET_STUB.search(value)
    if m:
        raise ValidationError("%s contains placeholder text: %r" % (name, m.group(0)))
    if _EM_DASH.search(value):
        raise ValidationError(
            "%s contains an em or en dash; the house style forbids them" % name)
