import html
import json

from tests.fixtures import make_guide, make_new_guide
from tpsermons.render import (guide_filename, guide_from_dict, guide_to_dict,
                              render_guide_page, render_markdown,
                              render_reflection_markdown, render_reflection_page,
                              render_site)


# --- classic mirrors the reference guide -------------------------------------

def test_classic_page_has_the_reference_guides_headings_in_order():
    page = render_guide_page(make_guide())
    order = ["At a Glance", "Before You Begin", "Opening", "Section 1:", "Section 2:",
             "Section 3:", "Closing and Application", "Facilitator Cheat Sheet",
             "Key Themes to Reinforce"]
    positions = [page.index(h) for h in order]
    assert positions == sorted(positions)


def test_classic_header_block_credits_preacher_with_role_and_church():
    page = render_guide_page(make_guide())
    assert "Aaron Brockett, Lead Pastor" in page
    assert "Traders Point Christian Church" in page
    assert "Position or Presence" in page and "Presence Over Position" in page


def test_classic_keeps_the_reference_guides_framing_lines():
    page = render_guide_page(make_guide())
    assert "They are for you, not to be read aloud." in page
    assert "Then pick one icebreaker based on your group." in page
    assert "Do not read them aloud." in page
    assert "(10 minutes)" in page and "(12-15 minutes)" in page and "(5 minutes)" in page


def test_classic_question_shows_lead_then_bold_ask():
    g = make_guide()
    page = render_guide_page(g)
    q = g.sections[0].questions[0]
    assert page.index(q.lead) < page.index(q.ask)
    assert "<th>Dynamic</th><th>What to do</th>" in page


def test_classic_key_themes_bold_their_labels():
    assert "<strong>Formation over circumstances:</strong>" in render_guide_page(make_guide())


def test_nobody_is_expected_to_bring_a_pen():
    for page in (render_guide_page(make_guide()), render_guide_page(make_new_guide()),
                 render_reflection_page(make_guide()), render_markdown(make_guide())):
        assert "pen" not in page.lower().replace("open", "").replace("happen", "") \
            .replace("spent", "").replace("depend", "").replace("expens", "")


def test_classic_markdown_matches_the_reference_structure():
    md = render_markdown(make_guide())
    for h in ("## At a Glance", "## Before You Begin", "## Opening (10 minutes)",
              "## Section 1: Section 0 (12-15 minutes)", "## Closing and Application (5 minutes)",
              "| Dynamic | What to do |", "## Key Themes to Reinforce", "**Materials:**"):
        assert h in md, h


# --- new is built for leading live -------------------------------------------

def test_new_page_has_a_tappable_run_of_show():
    page = render_guide_page(make_new_guide())
    assert "class='runshow" in page
    for anchor in ("#open", "#s1", "#s2", "#s3", "#honest", "#close"):
        assert "href='%s'" % anchor in page
        assert "id='%s'" % anchor[1:] in page


def test_new_page_carries_the_leading_aids():
    g = make_new_guide()
    page = render_guide_page(g)
    for needed in (g.thesis, g.outline[0], g.sensitivities[0], g.obstacle, g.carry,
                   g.sections[0].say, g.sections[0].questions[0].probe, "Must ask",
                   "Mark 9:33-37"):
        assert html.escape(needed) in page, needed


def test_new_page_has_no_clock():
    page = render_guide_page(make_new_guide())
    assert "minutes)" not in page


def test_classic_page_has_none_of_the_new_aids():
    page = render_guide_page(make_guide())
    for extra in ("runshow", "Must ask", "Get honest", "Next week we ask", "Follow up"):
        assert extra not in page, extra


# --- shared ------------------------------------------------------------------

def test_reflection_sheet_is_first_person_and_free_of_leader_material():
    for g in (make_guide(), make_new_guide()):
        sheet = render_reflection_page(g)
        assert g.sections[0].reflection_questions[0] in sheet
        assert g.sections[0].questions[0].ask not in sheet
        assert "Before You Begin" not in sheet and "Cheat" not in sheet
        assert "phone" in sheet
    assert "Someone here is in a hard season" not in render_reflection_page(make_new_guide())


def test_reflection_markdown_is_stripped_down():
    md = render_reflection_markdown(make_guide())
    assert "Before You Begin" not in md and "## This Week" in md


def test_filenames_distinguish_editions_and_documents():
    assert guide_filename(make_guide(), "html") == "2026-08-30-presence-over-position.html"
    assert guide_filename(make_new_guide(), "html") == "2026-08-30-presence-over-position-new.html"
    assert guide_filename(make_new_guide(), "html", "reflection") == \
        "2026-08-30-presence-over-position-new-reflection.html"


def test_toggle_is_labelled_new_and_classic_only_when_both_exist():
    assert "mode-toggle" not in render_guide_page(make_guide())
    page = render_guide_page(make_guide(), alt_href="x-new.html")
    assert ">New<" in page and ">Classic<" in page and "Modern" not in page


def test_both_editions_roundtrip_through_json():
    for g in (make_guide(), make_new_guide()):
        back = guide_from_dict(json.loads(json.dumps(guide_to_dict(g))))
        back.validate()
        assert back.mode == g.mode and back.question_count == g.question_count
        assert back.speaker_role == "Lead Pastor"


def test_index_lists_each_week_once_and_opens_new_by_default():
    site = render_site([make_guide(), make_new_guide()])
    assert site.count("class='featured") == 1
    assert "href='guides/2026-08-30-presence-over-position-new.html'" in site
    assert "data-classic='guides/2026-08-30-presence-over-position.html'" in site


def test_index_falls_back_to_classic_when_no_new_edition():
    assert "href='guides/2026-08-30-presence-over-position.html'" in render_site([make_guide()])
