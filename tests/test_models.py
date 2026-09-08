import pytest
from tpsermons.models import (SEGMENTS, DiscussBlock, Guide, ValidationError)


def blocks(n=3, probes=2):
    return [DiscussBlock(heading="Heading %d" % i,
                         question="What did that look like for you?",
                         probes=["Probe %d" % j for j in range(probes)])
            for i in range(n)]


def guide(**kw):
    base = dict(
        title="T", series="S", speaker=None, date="2026-08-30", passage="Mark 9:30-50",
        links={"tpcc": "https://tpcc.org/messages/x"},
        leader_notes=["Keep your own talking under a quarter of the night.",
                      "This one may be raw for a couple of guys."],
        opener="When did you last change your mind about something important?",
        context=" ".join(["word"] * 30),
        read_aloud="Read Mark 9:30-50 aloud; listen for what the disciples argue about.",
        observation="What did Jesus actually say when he caught them arguing?",
        discuss=blocks(),
        obstacle="What is most likely to stop you doing that by next Thursday?",
        commit=" ".join(["word"] * 40),
        carry="Next week we ask each other how that conversation went.",
        source="whisper",
    )
    base.update(kw)
    return Guide(**base)


def test_valid_guide_passes():
    guide().validate()


def test_evening_fits_the_45_to_60_minute_window():
    total = sum(m for _, m, _ in SEGMENTS)
    assert 45 <= total <= 60


def test_deep_questions_happen_in_subgroups():
    # Twelve men in one circle means three or four carry the room.
    modes = {label: mode for label, _, mode in SEGMENTS}
    assert "four" in modes["Dig in"]


@pytest.mark.parametrize("kw", [
    dict(discuss=blocks(n=2)),
    dict(discuss=blocks(n=4)),
    dict(discuss=blocks(probes=1)),
    dict(discuss=blocks(probes=4)),
    dict(leader_notes=["only one"]),
    dict(leader_notes=["a", "b", "c", "d", "e"]),
    dict(context="too short"),
])
def test_invalid_shapes_rejected(kw):
    with pytest.raises(ValidationError):
        guide(**kw).validate()


@pytest.mark.parametrize("field", ["opener", "observation", "obstacle"])
def test_prompts_must_actually_be_questions(field):
    with pytest.raises(ValidationError):
        guide(**{field: "This is a statement."}).validate()


def test_placeholder_tokens_rejected():
    with pytest.raises(ValidationError):
        guide(opener="TODO write the opener?").validate()


def test_ellipsis_and_asr_markers_are_not_placeholders():
    guide(carry="We will ask how it went ... [inaudible] and follow up.").validate()


def test_tpcc_link_is_required():
    with pytest.raises(ValidationError):
        guide(links={"youtube": "https://youtu.be/x"}).validate()


@pytest.mark.parametrize("bad", [
    "Have you ever thought about this?",
    "Do you struggle with pride?",
    "Is there something you would change?",
    "Can you see how that applies?",
])
def test_closed_questions_are_rejected(bad):
    # One-word answers stall a room of twelve. Ask When/Where/What/Who.
    with pytest.raises(ValidationError):
        guide(opener=bad).validate()


def test_obstacle_must_be_about_the_man_not_the_world():
    with pytest.raises(ValidationError):
        guide(obstacle="What makes this hard in our culture today?").validate()
    guide(obstacle="What will realistically stop you before next Thursday?").validate()
