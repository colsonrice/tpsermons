import pathlib

from tpsermons.tpcc import (find_speaker, find_transcript_url, find_video_id,
                            parse_series_page, series_slug)

FIX = pathlib.Path(__file__).parent / "fixtures"
SERIES = (FIX / "series_page.html").read_text(encoding="utf-8")
MESSAGE = (FIX / "message_page.html").read_text(encoding="utf-8")
NO_TRANSCRIPT = (FIX / "message_page_no_transcript.html").read_text(encoding="utf-8")


def test_series_slug_derives_from_series_name():
    assert series_slug("The Urgent Kingdom") == "the-urgent-kingdom"


def test_series_page_maps_titles_to_slugs():
    m = parse_series_page(SERIES)
    assert m["presence over position"] == "presence-over-position"


def test_map_handles_irregular_slugs_that_titles_cannot_produce():
    # "Enough" -> enough-1, and a title sharing no words with its slug.
    # These are why the slug is looked up rather than derived.
    m = parse_series_page(SERIES)
    assert m["enough"] == "enough-1"
    assert m["why you are exhausted"] == "rest-killers"


def test_library_link_is_not_treated_as_a_message():
    assert all(s != "#message-search" for s in parse_series_page(SERIES).values())


def test_finds_embedded_message_video_id():
    assert find_video_id(MESSAGE) == "cAmHuBCSFvo"


def test_finds_transcript_url_when_present():
    url = find_transcript_url(MESSAGE)
    assert url and "15637583-6f52-4672-b5dc-ea9603c36adf" in url


def test_transcript_url_is_none_for_a_recent_message():
    # Transcripts lag ~8 days, so a fresh sermon has none.
    assert find_transcript_url(NO_TRANSCRIPT) is None


def test_extracts_speaker_from_description_prose():
    assert find_speaker(MESSAGE) == "Chad Lunsford"


def test_speaker_is_none_when_absent_rather_than_raising():
    assert find_speaker(NO_TRANSCRIPT) is None
