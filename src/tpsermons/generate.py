"""Guide generation.

The model writes prose only. Every piece of metadata (title, series, date,
passage, speaker, role, links) is injected by code from sources resolved
upstream. Anything the model emits under those keys is discarded, so
hallucinated links and invented speaker names are structurally impossible.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

from .models import (CheatRow, Episode, Guide, Icebreaker, Question, Section,
                     ValidationError, normalize_guide)

MODEL = os.environ.get("OPENAI_MODEL") or "gpt-4o"
PROMPTS = Path(__file__).resolve().parents[2] / "prompts"

_COMMON_KEYS = '''{"guide_title": str,
 "goal": str,
 "scripture_instructions": str,
 "icebreakers": [{"label": "A", "fits": str, "question": str, "note": str},
                 {"label": "B", ...}, {"label": "C", ...}],
 "sections": [SECTION, ...],
 "closing_go_around": str,
 "prayer": str,
 "cheat_sheet": [{"dynamic": str, "response": str}, ...],
 "key_themes": [str, ...],
 "commitment_prompt": str,
 EDITION_KEYS}'''

_HINTS = {
    "classic": {
        "section": '{"title": str, "minutes": str, "setup": str, '
                   '"questions": [{"lead": str, "ask": str}, ...], '
                   '"reflection_questions": [str, ...]}',
        "edition": '"leader_notes": [str, str, str, str]',
        "notes": "Four or five leader_notes paragraphs totalling 500 to 700 words. "
                 "Every section setup is three to five sentences.",
    },
    "new": {
        "section": '{"title": str, "say": str, "setup": str, '
                   '"questions": [{"lead": str, "ask": str, "probe": str, '
                   '"star": bool}, ...], "reflection_questions": [str, ...]}',
        "edition": '"thesis": str, "outline": [str, ...], "sensitivities": [str, ...], '
                   '"read_refs": [str, ...], "obstacle": str, "carry": str',
        "notes": "One or two read_refs with verse numbers. Every question has a probe. "
                 "Exactly one question per section has star true.",
    },
}


def _schema_hint(mode: str) -> str:
    h = _HINTS[mode]
    return ("Return JSON with exactly these keys:\n%s\n\nSECTION is %s\n\n"
            "Exactly three icebreakers labelled A, B, C. Three sections with four or "
            "five questions each, or four sections with three or four each: twelve to "
            "fifteen questions in total. One first-person reflection question per "
            "question, same order. Five to seven key_themes and cheat_sheet rows. %s "
            "No em dashes anywhere."
            % (_COMMON_KEYS.replace("EDITION_KEYS", h["edition"]), h["section"], h["notes"]))


def build_guide(episode: Episode, payload: Dict, links: Dict[str, str],
                speaker: Optional[str], source: str, mode: str = "classic",
                speaker_role: Optional[str] = None) -> Guide:
    """Merge model prose with code-supplied metadata, repair, then validate."""
    new = mode == "new"
    try:
        sections = []
        for x in payload["sections"]:
            qs = []
            for q in x["questions"]:
                if isinstance(q, str):          # tolerate a bare string
                    q = {"ask": q}
                qs.append(Question(ask=q["ask"], lead=q.get("lead", ""),
                                   probe=q.get("probe", "") if new else "",
                                   star=bool(q.get("star", False)) if new else False))
            sections.append(Section(
                title=x["title"], setup=x["setup"], questions=qs,
                reflection_questions=list(x["reflection_questions"]),
                minutes=str(x.get("minutes", "")) if not new else "",
                say=x.get("say", "") if new else ""))
        ice = [Icebreaker(label=x["label"], fits=x["fits"], question=x["question"],
                          note=x.get("note", "")) for x in payload["icebreakers"]]
        cheat = [CheatRow(x["dynamic"], x["response"]) for x in payload["cheat_sheet"]]
        guide = Guide(
            title=episode.title, series=episode.series, speaker=speaker,
            date=episode.pub_date.strftime("%Y-%m-%d"), passage=episode.passage,
            links=dict(links), source=source, mode=mode, speaker_role=speaker_role,
            guide_title=payload["guide_title"], goal=payload["goal"],
            scripture_instructions=payload["scripture_instructions"],
            icebreakers=ice, sections=sections,
            closing_go_around=payload["closing_go_around"], prayer=payload["prayer"],
            cheat_sheet=cheat, key_themes=list(payload["key_themes"]),
            commitment_prompt=payload["commitment_prompt"],
            leader_notes=list(payload.get("leader_notes", [])) if not new else [],
            thesis=payload.get("thesis", "") if new else "",
            outline=list(payload.get("outline", [])) if new else [],
            sensitivities=list(payload.get("sensitivities", [])) if new else [],
            read_refs=list(payload.get("read_refs", [])) if new else [],
            obstacle=payload.get("obstacle", "") if new else "",
            carry=payload.get("carry", "") if new else "",
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValidationError("model output missing or malformed: %s" % exc)
    return normalize_guide(guide).validate()


def build_prompt(episode: Episode, transcript: str, speaker=None,
                 mode: str = "classic", speaker_role=None) -> str:
    parts = [(PROMPTS / "common.md").read_text(encoding="utf-8"),
             (PROMPTS / ("%s.md" % mode)).read_text(encoding="utf-8"),
             _schema_hint(mode)]
    preacher = speaker or "(not identified)"
    if speaker and speaker_role:
        preacher = "%s, %s" % (speaker, speaker_role)
    return (
        "%s\n\nSermon title: %s\nSeries: %s\nScripture reference: %s\nPreacher: %s\n\n"
        "The metadata above is authoritative; prefer it over anything the transcript "
        "seems to say, since the transcript may be machine-generated.\n\n"
        "Transcript:\n%s\n"
    ) % ("\n\n".join(parts), episode.title, episode.series or "(unknown)",
         episode.passage or "(not identified)", preacher, transcript)


def generate(episode: Episode, transcript: str, links: Dict[str, str],
             speaker: Optional[str], source: str, client, mode: str = "classic",
             speaker_role: Optional[str] = None) -> Guide:  # pragma: no cover
    """Call the model, feeding every validation problem back on retry."""
    prompt = build_prompt(episode, transcript, speaker, mode, speaker_role)
    messages = [{"role": "user", "content": prompt}]
    last, raw = None, "{}"
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL, response_format={"type": "json_object"}, messages=messages)
            raw = resp.choices[0].message.content
            return build_guide(episode, json.loads(raw), links, speaker, source, mode,
                               speaker_role)
        except (ValidationError, ValueError) as exc:
            last = exc
            messages = messages[:1] + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content":
                    "That output was rejected for these problems: %s. Fix all of them "
                    "and return the complete corrected JSON." % exc},
            ]
            print("  %s attempt %d rejected: %s" % (mode, attempt + 1, exc))
    raise ValidationError("model output failed validation 3x: %s" % last)
