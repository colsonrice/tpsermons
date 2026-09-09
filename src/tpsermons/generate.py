"""Guide generation.

The model writes prose only. Every piece of metadata -- title, series, date,
passage, speaker, links -- is injected by code from sources already resolved
upstream. Anything the model emits under those keys is discarded, which makes
hallucinated links and invented speaker names structurally impossible rather
than merely unlikely.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .models import (CheatRow, Episode, Guide, Icebreaker, Section,
                     ValidationError)

MODEL = "gpt-4o"
FORMAT_DOC = Path(__file__).resolve().parents[2] / "prompts" / "guide_format.md"

_SCHEMA_HINT = """Return JSON with exactly these keys:
{"goal": str,
 "leader_notes": [str, str, str],
 "scripture_instructions": str,
 "icebreakers": [{"label": "A", "question": str, "fits": str},
                 {"label": "B", ...}, {"label": "C", ...}],
 "sections": [{"title": str,
               "setup": str,
               "questions": [str, ...],
               "reflection_questions": [str, ...]}],
 "closing_go_around": str,
 "prayer": str,
 "cheat_sheet": [{"dynamic": str, "response": str}],
 "key_themes": [str, ...],
 "commitment_prompt": str}

Three to five leader_notes paragraphs. Exactly three icebreakers, labelled
A, B, C in order. Three or four sections, each with two to four questions and
exactly one first-person reflection_question per question, in the same order.
Twelve to fifteen questions across all sections. Five to seven key_themes and
five to seven cheat_sheet rows. No em dashes anywhere."""


def build_guide(episode: Episode, payload: Dict, links: Dict[str, str],
                speaker: Optional[str], source: str) -> Guide:
    """Merge model prose with code-supplied metadata, then validate."""
    try:
        sections = [Section(title=x["title"], setup=x["setup"],
                            questions=list(x["questions"]),
                            reflection_questions=list(x["reflection_questions"]))
                    for x in payload["sections"]]
        ice = [Icebreaker(label=x["label"], question=x["question"], fits=x["fits"])
               for x in payload["icebreakers"]]
        cheat = [CheatRow(dynamic=x["dynamic"], response=x["response"])
                 for x in payload["cheat_sheet"]]
        guide = Guide(
            title=episode.title,
            series=episode.series,
            speaker=speaker,
            date=episode.pub_date.strftime("%Y-%m-%d"),
            passage=episode.passage,
            links=dict(links),
            goal=payload["goal"],
            leader_notes=list(payload["leader_notes"]),
            scripture_instructions=payload["scripture_instructions"],
            icebreakers=ice,
            sections=sections,
            closing_go_around=payload["closing_go_around"],
            prayer=payload["prayer"],
            cheat_sheet=cheat,
            key_themes=list(payload["key_themes"]),
            commitment_prompt=payload["commitment_prompt"],
            source=source,
        )
    except (KeyError, TypeError) as exc:
        raise ValidationError("model output missing or malformed: %s" % exc)
    return guide.validate()


def build_prompt(episode: Episode, transcript: str, speaker=None) -> str:
    fmt = FORMAT_DOC.read_text(encoding="utf-8") if FORMAT_DOC.exists() else ""
    passage = episode.passage or "(not identified)"
    return (
        "%s\n\n%s\n\n"
        "Sermon title: %s\nSeries: %s\nScripture reference: %s\nSpeaker: %s\n\n"
        "The metadata above is authoritative; prefer it over anything the "
        "transcript seems to say, since the transcript may be machine-generated.\n\n"
        "Transcript:\n%s\n"
    ) % (fmt, _SCHEMA_HINT, episode.title, episode.series or "(unknown)", passage,
         speaker or "(unknown)", transcript)


def generate(episode: Episode, transcript: str, links: Dict[str, str],
             speaker: Optional[str], source: str, client) -> Guide:  # pragma: no cover
    """Call the model, retrying once when the shape is wrong."""
    prompt = build_prompt(episode, transcript, speaker)
    messages = [{"role": "user", "content": prompt}]
    last, raw = None, "{}"
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=messages,
            )
            raw = resp.choices[0].message.content
            payload = json.loads(raw)
            return build_guide(episode, payload, links, speaker, source)
        except (ValidationError, ValueError) as exc:
            last = exc
            # Tell the model what was wrong. Re-sending an identical prompt
            # just reproduces the same failure, which is exactly what happened
            # the first time this ran in CI.
            messages = messages[:1] + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content":
                    "That output was rejected: %s. Fix only that problem and "
                    "return the corrected JSON, keeping everything else." % exc},
            ]
            print("  attempt %d rejected: %s" % (attempt + 1, exc))
    raise ValidationError("model output failed validation 3x: %s" % last)
