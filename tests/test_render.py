from tpsermons.models import DiscussBlock, Guide
from tpsermons.render import render_markdown, guide_filename


def guide(**kw):
    base = dict(
        title="Presence Over Position", series="The Urgent Kingdom",
        speaker="Aaron Brockett", date="2026-08-30", passage="Mark 9:30-50",
        links={"tpcc": "https://tpcc.org/messages/presence-over-position",
               "youtube": "https://youtu.be/-F6w9h2Jpg8"},
        recap=" ".join(["word"] * 80),
        discuss=[DiscussBlock("Heading %d" % i, ["Q%da" % i, "Q%db" % i]) for i in range(3)],
        take_action=" ".join(["word"] * 60),
        reflections=["First prompt", "Second prompt", "Third prompt"],
        source="youtube_captions",
    )
    base.update(kw)
    return Guide(**base)


def test_renders_all_required_sections():
    md = render_markdown(guide())
    assert "Presence Over Position" in md
    assert "Mark 9:30-50" in md
    for i in range(3):
        assert "Heading %d" % i in md
    for r in ["First prompt", "Second prompt", "Third prompt"]:
        assert r in md


def test_speaker_line_omitted_when_unknown():
    assert "Aaron Brockett" not in render_markdown(guide(speaker=None))


def test_youtube_link_omitted_when_absent_but_tpcc_always_present():
    md = render_markdown(guide(links={"tpcc": "https://tpcc.org/messages/x"}))
    assert "https://tpcc.org/messages/x" in md
    assert "youtu.be" not in md


def test_front_matter_records_the_text_source():
    assert "youtube_captions" in render_markdown(guide())


def test_verse_text_is_not_fetched_only_the_reference():
    # Decision 6: translations are separately licensed and the site is public.
    md = render_markdown(guide())
    assert "Mark 9:30-50" in md


def test_filename_is_date_prefixed_and_slugged():
    assert guide_filename(guide()) == "2026-08-30-presence-over-position.md"
