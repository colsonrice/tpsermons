"""The source cascade: official transcript > YouTube captions > Whisper.

Ordered by fidelity then cost. The first two are free; Whisper fires only when
the others are unavailable. Fetchers are injected so the cascade is testable
without touching the network.
"""
from __future__ import annotations

from typing import Callable, Optional

from .models import Episode, SourcedText

Fetcher = Callable[[Episode], Optional[str]]

_ORDER = (("transcript_pdf", "pdf"), ("youtube_captions", "captions"), ("whisper", "whisper"))


def resolve_text(episode: Episode, pdf: Fetcher, captions: Fetcher,
                 whisper: Fetcher) -> Optional[SourcedText]:
    """Walk the cascade, returning the first source that yields real text."""
    fetchers = {"pdf": pdf, "captions": captions, "whisper": whisper}
    for label, key in _ORDER:
        try:
            text = fetchers[key](episode)
        except Exception:
            text = None
        if text and text.strip():
            return SourcedText(text=text.strip(), source=label)
    return None
