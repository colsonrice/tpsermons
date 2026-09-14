"""Cosmetic style problems are repaired in code, never allowed to kill a guide.

Three consecutive Monday runs failed because a retry fixed one em dash and the
model introduced a double-barrelled icebreaker. Punctuation is not worth
losing the week's guide over.
"""
import pytest

from tests.fixtures import make_guide, sections
from tpsermons.models import (Icebreaker, Section, ValidationError, normalize_guide)


def test_em_dashes_are_rewritten_not_rejected():
    g = normalize_guide(make_guide(goal="Move the room — quickly — to honesty."))
    assert "—" not in g.goal
    g.validate()


def test_en_dash_in_a_verse_range_becomes_a_hyphen():
    g = normalize_guide(make_guide(scripture_instructions="Read Mark 9:30–37 aloud."))
    assert "Mark 9:30-37" in g.scripture_instructions


def test_dashes_inside_leader_notes_are_repaired():
    notes = ["The sermon turns on one idea — presence.", "Second para.", "Third para."]
    g = normalize_guide(make_guide(leader_notes=notes))
    assert all("—" not in n for n in g.leader_notes)
    g.validate()


def test_double_barrelled_icebreaker_keeps_the_first_question():
    ice = [Icebreaker("A", "What's a hobby you pursued intensely? How did it shape you?",
                      "A newer group"),
           Icebreaker("B", "Think about a time you were overlooked.", "Storytellers"),
           Icebreaker("C", "Where are you keeping score?", "High trust")]
    g = normalize_guide(make_guide(icebreakers=ice))
    assert g.icebreakers[0].question == "What's a hobby you pursued intensely?"
    g.validate()


def test_double_barrelled_section_questions_are_trimmed_in_both_documents():
    secs = sections()
    s0 = secs[0]
    fixed = Section(s0.title, s0.setup,
                    ["Where have you drifted? What did it cost?"] + s0.questions[1:],
                    ["Where have I drifted? What did it cost me?"] + s0.reflection_questions[1:])
    g = normalize_guide(make_guide(sections=[fixed] + secs[1:]))
    assert g.sections[0].questions[0] == "Where have you drifted?"
    assert g.sections[0].reflection_questions[0] == "Where have I drifted?"
    g.validate()


def test_structural_problems_are_still_rejected():
    # Repair is for punctuation only. A thin guide is still a failure.
    with pytest.raises(ValidationError):
        normalize_guide(make_guide(sections=sections(3, 2))).validate()


def test_all_problems_are_reported_together():
    # One-at-a-time errors made the retry chase its tail.
    g = make_guide(sections=sections(3, 2), key_themes=["only one"])
    with pytest.raises(ValidationError) as exc:
        g.validate()
    msg = str(exc.value)
    assert "discussion questions" in msg and "key_themes" in msg
