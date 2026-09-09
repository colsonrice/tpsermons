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

from .models import DiscussBlock, Episode, Guide, ValidationError

MODEL = "gpt-4o"
FORMAT_DOC = Path(__file__).resolve().parents[2] / "prompts" / "guide_format.md"

_SCHEMA_HINT = """Return JSON with exactly these keys:
{"leader_notes": [str, str],
 "opener": str,
 "context": str,
 "read_refs": [str],
 "read_aloud": str,
 "observation": str,
 "discuss": [{"heading": str, "question": str, "probes": [str, str]} x3],
 "obstacle": str,
 "commit": str,
 "carry": str}

Two to four leader_notes. Exactly three discuss blocks, each with two or three
probes. opener, observation and obstacle must each be a question.

read_refs holds one or two SHORT verse ranges, e.g. ["Mark 10:2-9"] or
["Mark 10:2-9", "Mark 10:13-16"]. Never a bare chapter. Each entry must
include verse numbers."""


def build_guide(episode: Episode, payload: Dict, links: Dict[str, str],
                speaker: Optional[str], source: str) -> Guide:
    """Merge model prose with code-supplied metadata, then validate."""
    try:
        discuss = [DiscussBlock(heading=b["heading"], question=b["question"],
                                probes=list(b["probes"]))
                   for b in payload["discuss"]]
        guide = Guide(
            title=episode.title,
            series=episode.series,
            speaker=speaker,
            date=episode.pub_date.strftime("%Y-%m-%d"),
            passage=episode.passage,
            links=dict(links),
            leader_notes=list(payload["leader_notes"]),
            opener=payload["opener"],
            context=payload["context"],
            read_refs=list(payload["read_refs"]),
            read_aloud=payload["read_aloud"],
            observation=payload["observation"],
            discuss=discuss,
            obstacle=payload["obstacle"],
            commit=payload["commit"],
            carry=payload["carry"],
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
