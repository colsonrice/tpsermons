from datetime import datetime, timezone

import pytest

from tests.fixtures import make_guide, make_new_guide
from tpsermons.generate import build_guide, build_prompt
from tpsermons.models import Episode, ValidationError
from tpsermons.render import guide_to_dict

EP = Episode(guid="g", title="Presence Over Position",
             pub_date=datetime(2026, 8, 30, tzinfo=timezone.utc),
             mp3_url="https://x/y.mp3", series="The Urgent Kingdom", passage="Mark 9:30-50")
LINKS = {"tpcc": "https://tpcc.org/messages/presence-over-position"}
_META = ("title", "series", "speaker", "speaker_role", "date", "passage", "links",
         "source", "mode")


def payload(g, **kw):
    d = {k: v for k, v in guide_to_dict(g).items() if k not in _META}
    d.update(kw)
    return d


def test_metadata_comes_from_code_not_the_model():
    g = build_guide(EP, payload(make_guide(), title="Hallucinated",
                                links={"tpcc": "https://evil.example"}),
                    LINKS, "Aaron Brockett", "whisper", "classic", "Lead Pastor")
    assert g.title == "Presence Over Position" and g.links == LINKS
    assert g.speaker == "Aaron Brockett" and g.speaker_role == "Lead Pastor"


def test_classic_build_ignores_new_only_fields():
    g = build_guide(EP, dict(payload(make_new_guide()), **payload(make_guide())), LINKS,
                    None, "whisper", "classic")
    assert g.thesis == "" and g.obstacle == "" and not g.read_refs
    assert not any(q.star or q.probe for s in g.sections for q in s.questions)


def test_new_build_keeps_its_aids():
    g = build_guide(EP, payload(make_new_guide()), LINKS, None, "whisper", "new")
    assert g.mode == "new" and g.thesis and g.carry and g.sections[0].say


def test_bare_string_questions_are_tolerated():
    d = payload(make_guide())
    for s in d["sections"]:
        s["questions"] = [q["ask"] for q in s["questions"]]
    build_guide(EP, d, LINKS, None, "whisper", "classic")


def test_malformed_output_is_a_validation_error():
    d = payload(make_guide())
    del d["cheat_sheet"]
    with pytest.raises(ValidationError):
        build_guide(EP, d, LINKS, None, "whisper", "classic")


def test_prompt_layers_shared_rules_with_the_edition_spec():
    classic = build_prompt(EP, "transcript", "Aaron Brockett", "classic", "Lead Pastor")
    new = build_prompt(EP, "transcript", "Aaron Brockett", "new", "Lead Pastor")
    assert "Never assume anyone has a pen" in classic and "Never assume anyone has a pen" in new
    assert "Classic edition" in classic and "New edition" not in classic
    assert "New edition" in new and "led live from a phone" in new
    assert "Preacher: Aaron Brockett, Lead Pastor" in classic
