import pytest

from tests.fixtures import make_guide, make_new_guide, sections
from tpsermons.models import (DEFAULT_MODE, MODES, Question, Section, ValidationError,
                              normalize_guide)


def test_editions_are_named_new_and_classic():
    assert MODES == ("classic", "new") and DEFAULT_MODE == "new"


def test_valid_guides_pass():
    make_guide().validate()
    make_new_guide().validate()


def test_question_count_window_matches_the_reference_guide():
    make_guide(sections=sections(3, 4)).validate()                   # 12
    s = sections(3, 4)
    five = Section(s[0].title, s[0].setup, s[0].questions + [s[0].questions[0]],
                   s[0].reflection_questions + [s[0].reflection_questions[0]], "12-15")
    make_guide(sections=[five] + s[1:]).validate()                   # 5,4,4 = 13
    with pytest.raises(ValidationError):
        make_guide(sections=sections(3, 3)).validate()               # 9
    with pytest.raises(ValidationError):
        make_guide(sections=sections(4, 4)).validate()               # 16


def test_never_more_than_four_sections():
    with pytest.raises(ValidationError):
        make_guide(sections=sections(5, 3)).validate()


def test_count_rejection_says_how_many_to_add():
    with pytest.raises(ValidationError) as exc:
        make_guide(sections=sections(3, 3)).validate()
    assert "add 3 more" in str(exc.value)


def test_classic_needs_substantial_leader_notes():
    # The reference guide's notes run about 700 words; three thin lines fail.
    with pytest.raises(ValidationError) as exc:
        make_guide(leader_notes=["Short.", "Also short.", "Still short."]).validate()
    assert "leader_notes total" in str(exc.value)


def test_classic_section_setups_need_substance():
    s = sections()
    thin = Section(s[0].title, "Too short.", s[0].questions, s[0].reflection_questions, "12-15")
    with pytest.raises(ValidationError):
        make_guide(sections=[thin] + s[1:]).validate()


def test_new_edition_requires_its_leading_aids():
    for kw in (dict(thesis=""), dict(obstacle=""), dict(carry=""),
               dict(outline=["only one"]), dict(read_refs=["Mark 9"])):
        with pytest.raises(ValidationError):
            make_new_guide(**kw).validate()


def test_new_edition_needs_a_follow_up_under_every_question():
    s = sections(edition="new")
    bare = Section(s[0].title, s[0].setup, [Question(q.ask, q.lead, "", q.star)
                                            for q in s[0].questions],
                   s[0].reflection_questions, say=s[0].say)
    with pytest.raises(ValidationError):
        make_new_guide(sections=[bare] + s[1:]).validate()


def test_new_edition_does_not_need_classic_leader_notes():
    make_new_guide(leader_notes=[]).validate()


def test_double_barrelled_asks_are_rejected_but_imperatives_allowed():
    s = sections()
    two = Section(s[0].title, s[0].setup,
                  [Question("How do you see this? Where does it land?")] * 4,
                  s[0].reflection_questions, "12-15")
    with pytest.raises(ValidationError):
        make_guide(sections=[two] + s[1:]).validate()
    imp = Section(s[0].title, s[0].setup,
                  [Question("Think about a time you were overlooked.")] * 4,
                  ["Think about a time I was overlooked."] * 4, "12-15")
    make_guide(sections=[imp] + s[1:]).validate()


def test_icebreakers_labelled_in_order():
    g = make_guide()
    with pytest.raises(ValidationError):
        make_guide(icebreakers=g.icebreakers[:2]).validate()


def test_reflection_questions_mirror_the_guide():
    s = sections()
    short = Section(s[0].title, s[0].setup, s[0].questions, s[0].reflection_questions[:1], "12-15")
    with pytest.raises(ValidationError):
        make_guide(sections=[short] + s[1:]).validate()


def test_tpcc_link_required():
    with pytest.raises(ValidationError):
        make_guide(links={"youtube": "x"}).validate()


def test_all_problems_reported_together():
    with pytest.raises(ValidationError) as exc:
        make_guide(sections=sections(3, 3), key_themes=["one"]).validate()
    assert "discussion questions" in str(exc.value) and "key_themes" in str(exc.value)


# --- repair ------------------------------------------------------------------

def test_dashes_are_repaired_not_fatal():
    g = normalize_guide(make_guide(goal="Move the room — honestly.",
                                   scripture_instructions="Read Mark 9:30–37 aloud."))
    assert "—" not in g.goal and "Mark 9:30-37" in g.scripture_instructions
    g.validate()


def test_double_question_trimmed_to_first():
    s = sections()
    two = Section(s[0].title, s[0].setup,
                  [Question("Where have you drifted? What did it cost?")] + s[0].questions[1:],
                  s[0].reflection_questions, "12-15")
    g = normalize_guide(make_guide(sections=[two] + s[1:]))
    assert g.sections[0].questions[0].ask == "Where have you drifted?"


def test_new_edition_gets_exactly_one_must_ask_per_section():
    s = sections(edition="new")
    none = Section(s[0].title, s[0].setup, [Question(q.ask, q.lead, q.probe, False)
                                            for q in s[0].questions],
                   s[0].reflection_questions, say=s[0].say)
    many = Section(s[1].title, s[1].setup, [Question(q.ask, q.lead, q.probe, True)
                                            for q in s[1].questions],
                   s[1].reflection_questions, say=s[1].say)
    g = normalize_guide(make_new_guide(sections=[none, many, s[2]]))
    for sec in g.sections:
        assert sum(q.star for q in sec.questions) == 1


def test_classic_never_carries_stars():
    s = sections(edition="new")          # starred input
    g = normalize_guide(make_guide(sections=[Section(x.title, x.setup, x.questions,
                                                     x.reflection_questions, "12-15")
                                             for x in s]))
    assert not any(q.star for sec in g.sections for q in sec.questions)
