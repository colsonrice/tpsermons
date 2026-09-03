from datetime import datetime, timezone

from tpsermons.models import Episode
from tpsermons.source import resolve_text

EP = Episode(guid="g", title="T", pub_date=datetime(2026, 8, 30, tzinfo=timezone.utc),
             mp3_url="https://x/y.mp3", series="S", passage="Mark 9")


def resolve(pdf=None, captions=None, whisper=None):
    return resolve_text(EP,
                        pdf=lambda e: pdf,
                        captions=lambda e: captions,
                        whisper=lambda e: whisper)


def test_prefers_official_transcript_when_present():
    got = resolve(pdf="official", captions="yt", whisper="w")
    assert got.text == "official"
    assert got.source == "transcript_pdf"


def test_falls_back_to_captions_when_transcript_not_yet_posted():
    got = resolve(pdf=None, captions="yt", whisper="w")
    assert got.source == "youtube_captions"


def test_falls_through_to_whisper_when_captions_unavailable():
    # Availability policy: never defer waiting on captions. A missing caption
    # track costs ~$0.15, not a week's delay.
    got = resolve(pdf=None, captions=None, whisper="w")
    assert got.source == "whisper"
    assert got.text == "w"


def test_returns_none_when_every_source_fails():
    assert resolve() is None


def test_blank_sources_are_treated_as_missing():
    got = resolve(pdf="   ", captions="real captions", whisper="w")
    assert got.source == "youtube_captions"
