from datetime import datetime, timezone

import pytest

from tpsermons.generate import build_guide
from tpsermons.models import Episode, ValidationError

EP = Episode(guid="g", title="Presence Over Position",
             pub_date=datetime(2026, 8, 30, tzinfo=timezone.utc),
             mp3_url="https://x/y.mp3", series="The Urgent Kingdom", passage="Mark 9:30-50")

LINKS = {"tpcc": "https://tpcc.org/messages/presence-over-position",
         "youtube": "https://youtu.be/-F6w9h2Jpg8"}


def payload(**kw):
    base = {
        "leader_notes": ["Talk less than a quarter of the night.",
                         "This may be raw for someone in the room."],
        "opener": "When did you last change your mind about something?",
        "context": " ".join(["word"] * 30),
        "read_aloud": "Read Mark 9 aloud; listen for the argument.",
        "observation": "What did Jesus actually say to them?",
        "discuss": [{"heading": "H%d" % i,
                     "question": "Where has that shown up for you?",
                     "probes": ["P1", "P2"]} for i in range(3)],
        "obstacle": "What will realistically stop you before next Thursday?",
        "commit": " ".join(["word"] * 40),
        "carry": "Next week we ask how that went.",
    }
    base.update(kw)
    return base


def test_metadata_comes_from_code_not_the_model():
    g = build_guide(EP, payload(), links=LINKS, speaker="Aaron Brockett", source="youtube_captions")
    assert g.title == "Presence Over Position"
    assert g.series == "The Urgent Kingdom"
    assert g.passage == "Mark 9:30-50"
    assert g.speaker == "Aaron Brockett"
    assert g.date == "2026-08-30"


def test_model_supplied_links_are_discarded():
    # Hallucinated URLs must be structurally impossible, not merely unlikely.
    g = build_guide(EP, payload(links={"tpcc": "https://evil.example"}),
                    links=LINKS, speaker=None, source="youtube_captions")
    assert g.links["tpcc"] == LINKS["tpcc"]
    assert "evil" not in str(g.links)


def test_model_supplied_title_is_discarded():
    g = build_guide(EP, payload(title="Hallucinated Title"), links=LINKS,
                    speaker=None, source="youtube_captions")
    assert g.title == "Presence Over Position"


def test_malformed_model_output_raises_validation_error():
    with pytest.raises(ValidationError):
        build_guide(EP, payload(discuss=payload()["discuss"][:2]), links=LINKS,
                    speaker=None, source="youtube_captions")


def test_missing_key_raises_validation_error():
    broken = payload()
    del broken["commit"]
    with pytest.raises(ValidationError):
        build_guide(EP, broken, links=LINKS, speaker=None, source="youtube_captions")


def test_terse_commitments_are_allowed():
    # "Call your brother before Thursday and apologize for Christmas" is a
    # good commitment. A word floor that rejects it is the rule's problem.
    terse = "Call your brother before Thursday and apologize for what you said."
    g = build_guide(EP, payload(commit=terse), links=LINKS, speaker=None,
                    source="whisper")
    assert g.commit == terse
