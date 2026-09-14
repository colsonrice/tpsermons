"""Boundary types.

`Guide` is the contract between `generate` and `render`. Metadata is injected
by code; only the prose is model-authored, so hallucinated links and invented
speaker names are structurally impossible.

Every sermon gets two editions:

- classic mirrors the group's own reference guide (Nick's PDF and written
  spec) section for section: rich leader notes, timed sections, lead-in plus
  bold question, cheat sheet, key themes.
- new is built to be led live from a phone: a run of show, a one-line thesis
  and outline instead of long notes, a line to say at each section, one
  must-ask question per section, a visible follow-up under every question,
  a Get Honest question and a carry question. No clock.

Both come with a participant reflection sheet in the first person. Nobody is
assumed to have a pen; the men read their Bibles on their phones.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

_PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME|XXX|Lorem)\b", re.IGNORECASE)
_BRACKET_STUB = re.compile(r"\[insert[^\]]*\]", re.IGNORECASE)
_EM_DASH = re.compile(r"[—–]")

MODES = ("classic", "new")
DEFAULT_MODE = "new"

SECTIONS = (3, 4)
QUESTIONS_PER_SECTION = (2, 5)     # the reference guide's first section has five
TOTAL_QUESTIONS = (12, 15)         # 12 to 14 ideal for 60 minutes
ICEBREAKERS = 3                    # labelled A / B / C
KEY_THEMES = (5, 7)
CHEAT_ROWS = (5, 7)

# classic
LEADER_NOTE_PARAS = (3, 5)
LEADER_NOTE_WORDS = 250            # floor; the reference guide's notes run ~700
SETUP_WORDS = 35                   # floor per section setup

# new
OUTLINE = (2, 5)
SENSITIVITIES = (0, 3)
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
    fits: str           # the group dynamic it suits
    question: str
    note: str = ""      # one short line to the leader on how to use it


@dataclass(frozen=True)
class Question:
    ask: str            # the bold question itself
    lead: str = ""      # plain lead-in anchoring it in the sermon
    probe: str = ""     # new: follow-up when answers stay on the surface
    star: bool = False  # new: the one to keep if time runs short


@dataclass(frozen=True)
class Section:
    title: str
    setup: str
    questions: List[Question]
    reflection_questions: List[str]   # first person, mirrors questions
    minutes: str = ""                 # classic: e.g. "12-15"
    say: str = ""                     # new: the line the leader reads aloud


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
    # --- authored by the model, both editions ---------------------------
    guide_title: str
    goal: str
    scripture_instructions: str
    icebreakers: List[Icebreaker]
    sections: List[Section]
    closing_go_around: str
    prayer: str
    cheat_sheet: List[CheatRow]
    key_themes: List[str]
    commitment_prompt: str
    source: str = ""
    mode: str = "classic"
    speaker_role: Optional[str] = None
    # --- classic ----------------------------------------------------------
    leader_notes: List[str] = field(default_factory=list)
    # --- new --------------------------------------------------------------
    thesis: str = ""
    outline: List[str] = field(default_factory=list)
    sensitivities: List[str] = field(default_factory=list)
    read_refs: List[str] = field(default_factory=list)
    obstacle: str = ""
    carry: str = ""

    @property
    def question_count(self) -> int:
        return sum(len(s.questions) for s in self.sections)

    def problems(self) -> List[str]:
        """Every validation problem at once, so a retry can fix them together."""
        found: List[str] = []

        def check(fn, *args):
            try:
                fn(*args)
            except ValidationError as exc:
                found.append(str(exc))

        if self.mode not in MODES:
            found.append("mode must be one of %s, got %r" % (MODES, self.mode))
        if not self.links.get("tpcc"):
            found.append("links.tpcc is required and is never omitted")

        for name in ("guide_title", "goal", "scripture_instructions",
                     "closing_go_around", "prayer", "commitment_prompt"):
            check(_text, name, getattr(self, name))

        if len(self.icebreakers) != ICEBREAKERS:
            found.append("expected %d icebreakers, got %d"
                         % (ICEBREAKERS, len(self.icebreakers)))
        for want, ice in zip("ABC", self.icebreakers):
            if ice.label.strip().upper() != want:
                found.append("icebreakers must be labelled A, B, C in order")
            check(_text, "icebreaker %s question" % want, ice.question)
            check(_single_question, "icebreaker %s" % want, ice.question)
            check(_text, "icebreaker %s fits" % want, ice.fits)

        check(_count, "sections", self.sections, *SECTIONS)
        qlo, qhi = QUESTIONS_PER_SECTION
        for i, sec in enumerate(self.sections):
            where = "sections[%d]" % i
            check(_text, where + ".title", sec.title)
            check(_text, where + ".setup", sec.setup)
            check(_count, where + ".questions", sec.questions, qlo, qhi)
            for q in sec.questions:
                check(_text, where + ".ask", q.ask)
                check(_single_question, where + ".ask", q.ask)
            if len(sec.reflection_questions) != len(sec.questions):
                found.append("%s has %d questions but %d reflection questions; the "
                             "sheet mirrors the guide"
                             % (where, len(sec.questions), len(sec.reflection_questions)))
            for r in sec.reflection_questions:
                check(_text, where + ".reflection", r)
                check(_single_question, where + ".reflection", r)

        tlo, thi = TOTAL_QUESTIONS
        n, secs = self.question_count, len(self.sections)
        if n < tlo:
            found.append("expected %d-%d discussion questions in total, got %d: add %d "
                         "more; with %d sections every section needs %s questions"
                         % (tlo, thi, n, tlo - n, secs, "4 or 5" if secs <= 3 else "3 or 4"))
        elif n > thi:
            found.append("expected %d-%d discussion questions in total, got %d: remove %d"
                         % (tlo, thi, n, n - thi))

        check(_count, "key_themes", self.key_themes, *KEY_THEMES)
        for t in self.key_themes:
            check(_text, "key_themes", t)
        check(_count, "cheat_sheet", self.cheat_sheet, *CHEAT_ROWS)
        for row in self.cheat_sheet:
            check(_text, "cheat_sheet.dynamic", row.dynamic)
            check(_text, "cheat_sheet.response", row.response)

        if self.mode == "classic":
            found += self._classic_problems(check)
        elif self.mode == "new":
            found += self._new_problems(check)
        return found

    def _classic_problems(self, check) -> List[str]:
        found: List[str] = []
        check(_count, "leader_notes", self.leader_notes, *LEADER_NOTE_PARAS)
        for p in self.leader_notes:
            check(_text, "leader_notes", p)
        words = sum(len(p.split()) for p in self.leader_notes)
        if self.leader_notes and words < LEADER_NOTE_WORDS:
            found.append("leader_notes total %d words; they need at least %d. Expand "
                         "them: the opening illustration, the turn in the passage, the "
                         "thesis, the preacher's outline, a word on this room, and the "
                         "pastoral sensitivities" % (words, LEADER_NOTE_WORDS))
        for i, sec in enumerate(self.sections):
            w = len(sec.setup.split())
            if w < SETUP_WORDS:
                found.append("sections[%d].setup is %d words; each setup needs at least "
                             "%d (three to five sentences)" % (i, w, SETUP_WORDS))
        return found

    def _new_problems(self, check) -> List[str]:
        found: List[str] = []
        check(_text, "thesis", self.thesis)
        check(_count, "outline", self.outline, *OUTLINE)
        for o in self.outline:
            check(_text, "outline", o)
        check(_count, "sensitivities", self.sensitivities, *SENSITIVITIES)
        for s in self.sensitivities:
            check(_text, "sensitivities", s)
        check(_count, "read_refs", self.read_refs, *READ_REFS)
        for r in self.read_refs:
            if not re.search(r"\d+:\d+", r or ""):
                found.append("read_refs entry %r must name verses, not a whole chapter" % r)
        check(_text, "obstacle", self.obstacle)
        check(_single_question, "obstacle", self.obstacle)
        check(_text, "carry", self.carry)
        for i, sec in enumerate(self.sections):
            check(_text, "sections[%d].say" % i, sec.say)
            for q in sec.questions:
                check(_text, "sections[%d].probe" % i, q.probe)
        return found

    def validate(self) -> "Guide":
        found = self.problems()
        if found:
            raise ValidationError("; ".join(found))
        return self


def _count(name, items, lo, hi) -> None:
    if not lo <= len(items) <= hi:
        raise ValidationError("expected %d-%d %s, got %d" % (lo, hi, name, len(items)))


def _text(name: str, value: str) -> None:
    if not value or not str(value).strip():
        raise ValidationError("%s is empty" % name)
    m = _PLACEHOLDER.search(value) or _BRACKET_STUB.search(value)
    if m:
        raise ValidationError("%s contains placeholder text: %r" % (name, m.group(0)))
    if _EM_DASH.search(value):
        raise ValidationError("%s contains an em or en dash" % name)


def _single_question(name: str, value: str) -> None:
    """At most one question mark per prompt.

    A lead-in sentence before one question is fine, and so is an imperative
    prompt with no question mark ("Think about a time when..."). Two questions
    let a man answer the easier one and skip the other.
    """
    marks = (value or "").count("?")
    if marks > 1:
        raise ValidationError("%s asks %d questions in one prompt: %r" % (name, marks, value))


# --- repair ------------------------------------------------------------------
#
# Punctuation-level house style is fixed mechanically rather than enforced by
# rejection. Three Monday runs were once lost to em dashes and a double
# question; none of that is worth losing the week's guide.

_DIGIT_DASH = re.compile(r"(?<=\d)\s*[—–]\s*(?=\d)")
_PROSE_DASH = re.compile(r"\s*[—–]\s*")


def _fix(text: str) -> str:
    if not text:
        return text
    text = _DIGIT_DASH.sub("-", text)          # Mark 9:30–37 -> Mark 9:30-37
    text = _PROSE_DASH.sub(", ", text)         # clause — clause -> clause, clause
    text = re.sub(r",\s*([,.;:?!])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _first_question(text: str) -> str:
    """Keep a prompt up to its first question mark if it asks more than one."""
    text = _fix(text)
    if text and text.count("?") > 1:
        text = text[:text.index("?") + 1]
    return text


def _repair_stars(questions: List[Question], edition: str) -> List[Question]:
    """New edition: exactly one must-ask per section. Classic: none."""
    if edition != "new":
        return [Question(q.ask, q.lead, q.probe, False) for q in questions]
    starred = [i for i, q in enumerate(questions) if q.star]
    keep = starred[0] if starred else 0
    return [Question(q.ask, q.lead, q.probe, i == keep) for i, q in enumerate(questions)]


def normalize_guide(g: Guide) -> Guide:
    """Return a copy with punctuation-level problems repaired."""
    sections = []
    for x in g.sections:
        qs = [Question(_first_question(q.ask), _fix(q.lead), _first_question(q.probe), q.star)
              for q in x.questions]
        sections.append(Section(
            title=_fix(x.title), setup=_fix(x.setup),
            questions=_repair_stars(qs, g.mode),
            reflection_questions=[_first_question(r) for r in x.reflection_questions],
            minutes=_fix(x.minutes), say=_fix(x.say)))
    return Guide(
        title=g.title, series=g.series, speaker=g.speaker, date=g.date,
        passage=g.passage, links=g.links, source=g.source, mode=g.mode,
        speaker_role=g.speaker_role,
        guide_title=_fix(g.guide_title), goal=_fix(g.goal),
        scripture_instructions=_fix(g.scripture_instructions),
        icebreakers=[Icebreaker(i.label, _fix(i.fits), _first_question(i.question),
                                _fix(i.note)) for i in g.icebreakers],
        sections=sections,
        closing_go_around=_fix(g.closing_go_around), prayer=_fix(g.prayer),
        cheat_sheet=[CheatRow(_fix(c.dynamic), _fix(c.response)) for c in g.cheat_sheet],
        key_themes=[_fix(t) for t in g.key_themes],
        commitment_prompt=_fix(g.commitment_prompt),
        leader_notes=[_fix(p) for p in g.leader_notes],
        thesis=_fix(g.thesis),
        outline=[_fix(o) for o in g.outline],
        sensitivities=[_fix(s) for s in g.sensitivities],
        read_refs=[_fix(r) for r in g.read_refs],
        obstacle=_first_question(g.obstacle),
        carry=_fix(g.carry),
    )
