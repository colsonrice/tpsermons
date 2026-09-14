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
from dataclasses import dataclass, field
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

# Two editions of every guide. Classic mirrors the group's original guide.
# Modern keeps that base and adds a few things: a Get Honest question, a
# carry question for next week, follow-up probes, and short verse ranges.
MODES = ("classic", "modern")
DEFAULT_MODE = "modern"
PROBES_PER_SECTION = (1, 2)
READ_REFS = (1, 2)


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
    probes: tuple = ()                # modern only: follow-ups if it stalls


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
    # --- modern edition only ------------------------------------------------
    mode: str = "classic"
    obstacle: Optional[str] = None          # Get Honest
    carry: Optional[str] = None             # Next week we ask
    read_refs: List[str] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return sum(len(s.questions) for s in self.sections)

    def problems(self) -> List[str]:
        """Every validation problem, so a retry can fix them all at once.

        Reporting one error at a time made the retry chase its tail: it fixed
        an em dash, introduced a double question, and ran out of attempts.
        """
        found: List[str] = []

        def check(fn, *args):
            try:
                fn(*args)
            except ValidationError as exc:
                found.append(str(exc))

        if "tpcc" not in self.links or not self.links["tpcc"]:
            found.append("links.tpcc is required and is never omitted")

        for name in ("goal", "scripture_instructions", "closing_go_around",
                     "prayer", "commitment_prompt"):
            check(_text, name, getattr(self, name))

        check(_count, "leader_notes", self.leader_notes, *LEADER_NOTE_PARAS)
        for n in self.leader_notes:
            check(_text, "leader_notes", n)

        if len(self.icebreakers) != ICEBREAKERS:
            found.append("expected %d icebreakers, got %d"
                         % (ICEBREAKERS, len(self.icebreakers)))
        for want, ice in zip("ABC", self.icebreakers):
            if ice.label.strip().upper() != want:
                found.append("icebreakers must be labelled A, B, C in order")
            check(_text, "icebreaker %s" % want, ice.question)
            check(_single_question, "icebreaker %s" % want, ice.question)
            check(_text, "icebreaker %s fits" % want, ice.fits)

        check(_count, "sections", self.sections, *SECTIONS)
        qlo, qhi = QUESTIONS_PER_SECTION
        for i, sec in enumerate(self.sections):
            check(_text, "sections[%d].title" % i, sec.title)
            check(_text, "sections[%d].setup" % i, sec.setup)
            check(_count, "sections[%d].questions" % i, sec.questions, qlo, qhi)
            for q in sec.questions:
                check(_text, "sections[%d].question" % i, q)
                check(_single_question, "sections[%d].question" % i, q)
            if len(sec.reflection_questions) != len(sec.questions):
                found.append(
                    "sections[%d] has %d questions but %d reflection questions; "
                    "the sheet mirrors the guide"
                    % (i, len(sec.questions), len(sec.reflection_questions)))
            for q in sec.reflection_questions:
                check(_text, "sections[%d].reflection" % i, q)
                check(_single_question, "sections[%d].reflection" % i, q)

        tlo, thi = TOTAL_QUESTIONS
        if not tlo <= self.question_count <= thi:
            n, secs = self.question_count, len(self.sections)
            if n < tlo:
                how = ("add %d more; with %d sections every section needs %s questions"
                       % (tlo - n, secs, "exactly 4" if secs <= 3 else "3 or 4"))
            else:
                how = "remove %d" % (n - thi)
            found.append("expected %d-%d discussion questions in total, got %d: %s"
                         % (tlo, thi, n, how))

        check(_count, "key_themes", self.key_themes, *KEY_THEMES)
        for t in self.key_themes:
            check(_text, "key_themes", t)
        check(_count, "cheat_sheet", self.cheat_sheet, *CHEAT_ROWS)
        for row in self.cheat_sheet:
            check(_text, "cheat_sheet.dynamic", row.dynamic)
            check(_text, "cheat_sheet.response", row.response)

        if self.mode not in MODES:
            found.append("mode must be one of %s, got %r" % (MODES, self.mode))
        if self.mode == "modern":
            check(_text, "obstacle", self.obstacle or "")
            check(_single_question, "obstacle", self.obstacle or "")
            check(_text, "carry", self.carry or "")
            check(_count, "read_refs", self.read_refs, *READ_REFS)
            for r in self.read_refs:
                if not re.search(r"\d+:\d+", r or ""):
                    found.append("read_refs entry %r must name verses, not a whole "
                                 "chapter" % r)
            plo, phi = PROBES_PER_SECTION
            for i, sec in enumerate(self.sections):
                check(_count, "sections[%d].probes" % i, list(sec.probes), plo, phi)
                for pr in sec.probes:
                    check(_text, "sections[%d].probe" % i, pr)
        return found

    def validate(self) -> "Guide":
        found = self.problems()
        if found:
            raise ValidationError("; ".join(found))
        return self


# --- repair ------------------------------------------------------------------
#
# Punctuation-level house style is fixed mechanically rather than enforced by
# rejection. Three consecutive Monday runs were lost to em dashes and a
# double-barrelled icebreaker; none of those are worth losing the week's guide.

_DIGIT_DASH = re.compile(r"(?<=\d)\s*[—–]\s*(?=\d)")
_PROSE_DASH = re.compile(r"\s*[—–]\s*")


def _fix_dashes(text: str) -> str:
    if not text:
        return text
    text = _DIGIT_DASH.sub("-", text)          # Mark 9:30–37 -> Mark 9:30-37
    text = _PROSE_DASH.sub(", ", text)         # clause — clause -> clause, clause
    text = re.sub(r",\s*([,.;:?!])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _first_question(text: str) -> str:
    """Keep a prompt up to its first question mark if it asks more than one."""
    text = _fix_dashes(text)
    if text.count("?") > 1:
        text = text[:text.index("?") + 1]
    return text


def normalize_guide(g: "Guide") -> "Guide":
    """Return a copy with punctuation-level style problems repaired."""
    return Guide(
        title=g.title, series=g.series, speaker=g.speaker, date=g.date,
        passage=g.passage, links=g.links, source=g.source,
        goal=_fix_dashes(g.goal),
        leader_notes=[_fix_dashes(n) for n in g.leader_notes],
        scripture_instructions=_fix_dashes(g.scripture_instructions),
        icebreakers=[Icebreaker(i.label, _first_question(i.question), _fix_dashes(i.fits))
                     for i in g.icebreakers],
        sections=[Section(_fix_dashes(x.title), _fix_dashes(x.setup),
                          [_first_question(q) for q in x.questions],
                          [_first_question(q) for q in x.reflection_questions],
                          tuple(_first_question(pr) for pr in x.probes))
                  for x in g.sections],
        closing_go_around=_fix_dashes(g.closing_go_around),
        prayer=_fix_dashes(g.prayer),
        cheat_sheet=[CheatRow(_fix_dashes(c.dynamic), _fix_dashes(c.response))
                     for c in g.cheat_sheet],
        key_themes=[_fix_dashes(t) for t in g.key_themes],
        commitment_prompt=_fix_dashes(g.commitment_prompt),
        mode=g.mode,
        obstacle=_first_question(g.obstacle) if g.obstacle else g.obstacle,
        carry=_fix_dashes(g.carry) if g.carry else g.carry,
        read_refs=[_fix_dashes(r) for r in g.read_refs],
    )


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
