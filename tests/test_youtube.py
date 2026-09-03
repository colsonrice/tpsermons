import json
import pathlib

from tpsermons.youtube import normalize_cues

FIX = pathlib.Path(__file__).parent / "fixtures"
CUES = json.loads((FIX / "cues.json").read_text(encoding="utf-8"))


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
