from datetime import datetime, timezone

import pytest

from tests.fixtures import make_guide
from tpsermons.generate import build_guide
from tpsermons.models import Episode, ValidationError

EP = Episode(guid="g", title="Presence Over Position",
             pub_date=datetime(2026, 8, 30, tzinfo=timezone.utc),
             mp3_url="https://x/y.mp3", series="The Urgent Kingdom",
             passage="Mark 9:30-50")

LINKS = {"tpcc": "https://tpcc.org/messages/presence-over-position",
         "youtube": "https://youtu.be/-F6w9h2Jpg8"}


def payload(**kw):
    g = make_guide()
    base = {
        "goal": g.goal,
        "leader_notes": list(g.leader_notes),
        "scripture_instructions": g.scripture_instructions,
        "icebreakers": [{"label": i.label, "question": i.question, "fits": i.fits}
                        for i in g.icebreakers],
        "sections": [{"title": s.title, "setup": s.setup,
                      "questions": list(s.questions),
                      "reflection_questions": list(s.reflection_questions)}
                     for s in g.sections],
        "closing_go_around": g.closing_go_around,
        "prayer": g.prayer,
        "cheat_sheet": [{"dynamic": c.dynamic, "response": c.response}
                        for c in g.cheat_sheet],
        "key_themes": list(g.key_themes),
        "commitment_prompt": g.commitment_prompt,
    }
    base.update(kw)
    return base


def test_metadata_comes_from_code_not_the_model():
    g = build_guide(EP, payload(), links=LINKS, speaker="Aaron Brockett",
                    source="whisper")
    assert g.title == "Presence Over Position"
    assert g.series == "The Urgent Kingdom"
    assert g.speaker == "Aaron Brockett"
    assert g.date == "2026-08-30"


def test_model_supplied_links_and_title_are_discarded():
    g = build_guide(EP, payload(links={"tpcc": "https://evil.example"},
                                title="Hallucinated"),
                    links=LINKS, speaker=None, source="whisper")
    assert g.links["tpcc"] == LINKS["tpcc"]
    assert "evil" not in str(g.links)
    assert g.title == "Presence Over Position"


def test_wrong_question_count_is_rejected():
    thin = payload()
    for s in thin["sections"]:
        s["questions"] = s["questions"][:2]
        s["reflection_questions"] = s["reflection_questions"][:2]
    with pytest.raises(ValidationError):
        build_guide(EP, thin, links=LINKS, speaker=None, source="whisper")


def test_missing_key_raises_validation_error():
    broken = payload()
    del broken["cheat_sheet"]
    with pytest.raises(ValidationError):
        build_guide(EP, broken, links=LINKS, speaker=None, source="whisper")


def test_em_dash_from_the_model_is_rejected():
    with pytest.raises(ValidationError):
        build_guide(EP, payload(goal="Move the room — fast."), links=LINKS,
                    speaker=None, source="whisper")
