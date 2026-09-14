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


# --- editions --------------------------------------------------------------

from tests.fixtures import make_modern_guide


def test_modern_filenames_carry_a_suffix_and_classic_keeps_the_original():
    assert guide_filename(make_guide(), "html") == "2026-08-30-presence-over-position.html"
    assert guide_filename(make_modern_guide(), "html") == \
        "2026-08-30-presence-over-position-modern.html"
    assert guide_filename(make_modern_guide(), "html", "reflection") == \
        "2026-08-30-presence-over-position-modern-reflection.html"


def test_modern_page_adds_the_four_extras():
    page = render_guide_page(make_modern_guide())
    assert "Get honest" in page and "Next week we ask" in page
    assert "If it stalls" in page and "Mark 9:33-37" in page


def test_classic_page_has_none_of_the_modern_extras():
    page = render_guide_page(make_guide())
    for extra in ("Get honest", "Next week we ask", "If it stalls", "ref-chip"):
        assert extra not in page, extra


def test_toggle_appears_only_when_the_other_edition_exists():
    assert "mode-toggle" not in render_guide_page(make_guide())
    page = render_guide_page(make_guide(), alt_href="x-modern.html")
    assert "mode-toggle" in page and "x-modern.html" in page


def test_modern_edition_roundtrips_through_json():
    back = guide_from_dict(json.loads(json.dumps(guide_to_dict(make_modern_guide()))))
    back.validate()
    assert back.mode == "modern" and back.obstacle and back.carry
    assert back.sections[0].probes


def test_old_single_edition_json_still_loads_as_classic():
    d = guide_to_dict(make_guide())
    for k in ("mode", "obstacle", "carry", "read_refs"):
        d.pop(k)
    for sec in d["sections"]:
        sec.pop("probes")
    assert guide_from_dict(d).mode == "classic"


def test_index_lists_each_week_once_and_defaults_to_modern():
    site = render_site([make_guide(), make_modern_guide()])
    assert site.count("Presence Over Position</h2>") == 1
    assert "href='guides/2026-08-30-presence-over-position-modern.html'" in site
    assert "data-classic='guides/2026-08-30-presence-over-position.html'" in site


def test_index_falls_back_to_classic_when_no_modern_edition_exists():
    site = render_site([make_guide()])
    assert "href='guides/2026-08-30-presence-over-position.html'" in site


def test_modern_edition_requires_its_extras():
    import pytest
    from tpsermons.models import ValidationError
    with pytest.raises(ValidationError):
        make_modern_guide(obstacle=None).validate()
    with pytest.raises(ValidationError):
        make_modern_guide(read_refs=["Mark 9"]).validate()
