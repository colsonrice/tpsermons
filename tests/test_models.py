import pytest

from tests.fixtures import make_guide, sections
from tpsermons.models import TOTAL_QUESTIONS, ValidationError


def test_valid_guide_passes():
    make_guide().validate()


def test_question_count_lands_in_the_hour_window():
    lo, hi = TOTAL_QUESTIONS
    assert (lo, hi) == (12, 15)          # 12 to 14 ideal for 60 minutes
    make_guide(sections=sections(3, 4)).validate()      # 12
    make_guide(sections=sections(4, 3)).validate()      # 12
    with pytest.raises(ValidationError):
        make_guide(sections=sections(3, 2)).validate()  # 6, too thin
    with pytest.raises(ValidationError):
        make_guide(sections=sections(4, 4)).validate()  # 16, too many


def test_never_more_than_four_sections():
    make_guide(sections=sections(4, 3)).validate()
    with pytest.raises(ValidationError):
        make_guide(sections=sections(5, 3)).validate()


def test_em_dashes_are_rejected_by_house_style():
    with pytest.raises(ValidationError):
        make_guide(goal="Move the room — quickly — to honesty.").validate()
    with pytest.raises(ValidationError):
        make_guide(prayer="Pray – briefly.").validate()


def test_have_you_ever_questions_are_allowed():
    # The group's spec explicitly prefers these over abstract prompts.
    secs = sections()
    assert secs[0].questions[0].startswith("Have you ever")
    make_guide(sections=secs).validate()


def test_exactly_three_icebreakers_labelled_in_order():
    g = make_guide()
    assert [i.label for i in g.icebreakers] == ["A", "B", "C"]
    with pytest.raises(ValidationError):
        make_guide(icebreakers=g.icebreakers[:2]).validate()


def test_reflection_questions_mirror_the_guide_questions():
    secs = sections()
    broken = list(secs)
    broken[0] = type(secs[0])(secs[0].title, secs[0].setup, secs[0].questions,
                              secs[0].reflection_questions[:1])
    with pytest.raises(ValidationError):
        make_guide(sections=broken).validate()


def test_leader_notes_are_three_to_five_paragraphs():
    make_guide(leader_notes=["a b c", "d e f", "g h i"]).validate()
    with pytest.raises(ValidationError):
        make_guide(leader_notes=["only", "two"]).validate()


def test_key_themes_and_cheat_sheet_bounds():
    g = make_guide()
    with pytest.raises(ValidationError):
        make_guide(key_themes=g.key_themes[:2]).validate()
    with pytest.raises(ValidationError):
        make_guide(cheat_sheet=g.cheat_sheet[:2]).validate()


def test_tpcc_link_is_required():
    with pytest.raises(ValidationError):
        make_guide(links={"youtube": "https://youtu.be/x"}).validate()
