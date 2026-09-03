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
{"recap": str,
 "discuss": [{"heading": str, "questions": [str, str]} x3],
 "take_action": str,
 "reflections": [str, str, str]}"""


def build_guide(episode: Episode, payload: Dict, links: Dict[str, str],
                speaker: Optional[str], source: str) -> Guide:
    """Merge model prose with code-supplied metadata, then validate."""
    try:
        discuss = [DiscussBlock(heading=b["heading"], questions=list(b["questions"]))
                   for b in payload["discuss"]]
        guide = Guide(
            title=episode.title,
            series=episode.series,
            speaker=speaker,
            date=episode.pub_date.strftime("%Y-%m-%d"),
            passage=episode.passage,
            links=dict(links),
            recap=payload["recap"],
            discuss=discuss,
            take_action=payload["take_action"],
            reflections=list(payload["reflections"]),
            source=source,
        )
    except (KeyError, TypeError) as exc:
        raise ValidationError("model output missing or malformed: %s" % exc)
    return guide.validate()


def build_prompt(episode: Episode, transcript: str) -> str:
    fmt = FORMAT_DOC.read_text(encoding="utf-8") if FORMAT_DOC.exists() else ""
    passage = episode.passage or "(not identified)"
    return (
        "%s\n\n%s\n\n"
        "Sermon title: %s\nSeries: %s\nScripture reference: %s\n\n"
        "The reference above is authoritative; prefer it over anything the "
        "transcript seems to say, since the transcript may be machine-generated.\n\n"
        "Transcript:\n%s\n"
    ) % (fmt, _SCHEMA_HINT, episode.title, episode.series or "(unknown)", passage, transcript)


def generate(episode: Episode, transcript: str, links: Dict[str, str],
             speaker: Optional[str], source: str, client) -> Guide:  # pragma: no cover
    """Call the model, retrying once when the shape is wrong."""
    prompt = build_prompt(episode, transcript)
    last = None
    for _ in range(2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            payload = json.loads(resp.choices[0].message.content)
            return build_guide(episode, payload, links, speaker, source)
        except (ValidationError, ValueError) as exc:
            last = exc
    raise ValidationError("model output failed validation twice: %s" % last)
