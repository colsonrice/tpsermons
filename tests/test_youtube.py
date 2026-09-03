import json
import pathlib

from tpsermons.youtube import find_video, normalize_cues

FIX = pathlib.Path(__file__).parent / "fixtures"
CHANNEL = (FIX / "channel.xml").read_text(encoding="utf-8")
CUES = json.loads((FIX / "cues.json").read_text(encoding="utf-8"))


def test_selects_message_only_cut_not_full_gathering():
    # Both cuts exist for every sermon. The Full Gathering cut carries ~3000
    # extra words of worship and announcements and must never be selected.
    vid = find_video(CHANNEL, "Presence Over Position | The Urgent Kingdom | Mark 9:30-50")
    assert vid == "-F6w9h2Jpg8"
    assert vid != "itp0FIVGEUs"


def test_returns_none_when_no_match():
    assert find_video(CHANNEL, "Nonexistent Sermon | Some Series | Mark 1:1") is None


def test_match_tolerates_whitespace_and_case_differences():
    vid = find_video(CHANNEL, "presence over position |  the urgent kingdom | Mark 9:30-50")
    assert vid == "-F6w9h2Jpg8"


def test_normalize_strips_bracketed_markers():
    text = normalize_cues(CUES)
    for marker in ("[music]", "[applause]", "[inaudible]"):
        assert marker not in text.lower()


def test_normalize_collapses_whitespace_and_joins_cues():
    text = normalize_cues(CUES)
    assert "  " not in text
    assert text == text.strip()
    assert "Well, good morning. How are we doing today?" in text


def test_normalize_preserves_legitimate_ellipsis():
    # An ellipsis inside a quotation is content, not a marker.
    assert "..." in normalize_cues(CUES)


def test_normalize_handles_empty_input():
    assert normalize_cues([]) == ""
