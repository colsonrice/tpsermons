import json

from tests.fixtures import make_guide
from tpsermons.render import (guide_filename, guide_from_dict, guide_to_dict,
                              render_guide_page, render_markdown,
                              render_reflection_markdown, render_reflection_page,
                              render_site)


def test_roundtrips_through_json():
    back = guide_from_dict(json.loads(json.dumps(guide_to_dict(make_guide()))))
    back.validate()
    assert back.question_count == make_guide().question_count
    assert [i.label for i in back.icebreakers] == ["A", "B", "C"]


def test_leader_guide_carries_all_the_scaffolding():
    page = render_guide_page(make_guide())
    for needed in ("Before you begin", "Opening", "Closing and application",
                   "Facilitator cheat sheet", "Key themes to reinforce",
                   "About 60 minutes"):
        assert needed in page, needed


def test_pastoral_flags_never_reach_the_participant_sheet():
    # Leader notes mention that divorce may be raw. That must not be handed out.
    g = make_guide()
    sheet = render_reflection_page(g)
    assert "Someone here has lived it" not in sheet
    assert "Before you begin" not in sheet
    assert "cheat sheet" not in sheet.lower()


def test_participant_sheet_uses_first_person_questions():
    g = make_guide()
    sheet = render_reflection_page(g)
    assert g.sections[0].reflection_questions[0] in sheet
    assert g.sections[0].questions[0] not in sheet


def test_participant_sheet_has_space_to_write():
    sheet = render_reflection_page(make_guide())
    assert "write" in sheet
    assert make_guide().commitment_prompt in sheet


def test_questions_are_numbered_continuously_across_sections():
    page = render_guide_page(make_guide())
    for n in (1, 5, 12):
        assert ">%d</span>" % n in page


def test_cheat_sheet_renders_as_a_table():
    page = render_guide_page(make_guide())
    assert "<table" in page and "<th>If this happens</th>" in page


def test_guide_links_to_the_reflection_sheet():
    page = render_guide_page(make_guide())
    assert guide_filename(make_guide(), "html", "reflection") in page


def test_filenames_distinguish_the_two_documents():
    g = make_guide()
    assert guide_filename(g, "md") == "2026-08-30-presence-over-position.md"
    assert guide_filename(g, "html", "reflection") == \
        "2026-08-30-presence-over-position-reflection.html"


def test_markdown_bolds_questions_and_tables_the_cheat_sheet():
    md = render_markdown(make_guide())
    assert "**Have you ever" in md
    assert "| If this happens | Try this |" in md
    assert "## Key Themes to Reinforce" in md


def test_reflection_markdown_is_stripped_down():
    md = render_reflection_markdown(make_guide())
    assert "Before You Begin" not in md
    assert "Cheat Sheet" not in md
    assert "## This Week" in md


def test_index_features_newest_and_archives_the_rest():
    site = render_site([make_guide(title="Older", date="2026-08-23"), make_guide()])
    assert "This week" in site and "Presence Over Position" in site and "Older" in site
