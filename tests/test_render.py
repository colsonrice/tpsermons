import json

from tpsermons.models import SEGMENTS, DiscussBlock, Guide
from tpsermons.render import (guide_filename, guide_from_dict, guide_to_dict,
                              render_guide_page, render_markdown, render_site)


def guide(**kw):
    base = dict(
        title="Presence Over Position", series="The Urgent Kingdom",
        speaker="Aaron Brockett", date="2026-08-30", passage="Mark 9:30-50",
        links={"tpcc": "https://tpcc.org/messages/presence-over-position",
               "youtube": "https://youtu.be/-F6w9h2Jpg8"},
        leader_notes=["Keep your own talking under a quarter of the night.",
                      "This may land hard for a couple of guys."],
        opener="When did you last want a title more than the work?",
        context=" ".join(["word"] * 30),
        read_refs=["Mark 9:33-37"],
        read_aloud="Listen for what they argue about on the road.",
        observation="What did Jesus say when he caught them arguing?",
        discuss=[DiscussBlock("Heading %d" % i, "Where has that shown up for you?",
                              ["Probe A", "Probe B"]) for i in range(3)],
        obstacle="What will realistically stop you this week?",
        commit=" ".join(["word"] * 40),
        carry="Next week we ask how that conversation went.",
        source="whisper",
    )
    base.update(kw)
    return Guide(**base)


def test_roundtrips_through_json():
    d = guide_to_dict(guide())
    back = guide_from_dict(json.loads(json.dumps(d)))
    assert back.opener == guide().opener
    assert len(back.discuss) == 3
    assert back.discuss[0].probes == ["Probe A", "Probe B"]
    back.validate()


def test_page_shows_every_movement():
    page = render_guide_page(guide())
    for label in SEGMENTS:
        assert label in page


def test_page_carries_no_clock_and_no_breakouts():
    page = render_guide_page(guide())
    for banned in ("min", "minutes", "groups of four", "Break into", "breakout"):
        assert banned not in page.replace("administ", ""), banned


def test_scripture_sections_are_shown_as_short_ranges():
    page = render_guide_page(guide(read_refs=["Mark 9:33-37", "Mark 9:42-48"]))
    assert "Mark 9:33-37" in page and "Mark 9:42-48" in page
    assert "ref-chip" in page


def test_probes_are_tucked_behind_a_disclosure():
    page = render_guide_page(guide())
    assert "<details" in page and "If it stalls" in page
    assert "Probe A" in page


def test_leader_notes_render_as_an_aside():
    page = render_guide_page(guide())
    assert "leader-notes" in page
    assert "quarter of the night" in page


def test_speaker_omitted_when_unknown():
    assert "Aaron Brockett" not in render_guide_page(guide(speaker=None))


def test_carry_closes_the_accountability_loop():
    assert "Next week we ask" in render_guide_page(guide())


def test_markdown_contains_the_full_script():
    md = render_markdown(guide())
    assert "## Leader Notes" in md
    assert "## Discuss" in md
    assert "## Get Honest" in md
    assert "Mark 9:33-37" in md
    assert "**Next week:**" in md
    assert "Probe A" in md


def test_filenames_are_date_prefixed():
    assert guide_filename(guide()) == "2026-08-30-presence-over-position.md"
    assert guide_filename(guide(), "html") == "2026-08-30-presence-over-position.html"


def test_index_features_newest_and_archives_the_rest():
    a, b = guide(), guide(title="Older One", date="2026-08-23")
    site = render_site([b, a])
    assert "This week" in site
    assert "Presence Over Position" in site
    assert "Older One" in site
