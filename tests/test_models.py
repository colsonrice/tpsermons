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
        read_refs=["Mark 9:33-37"],
        read_aloud="Listen for what the disciples argue about on the road.",
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


def test_segments_carry_no_clock_and_no_breakouts():
    # The group stays together and takes as long as a question deserves.
    assert SEGMENTS == ("Open", "Read", "Discuss", "Get Honest", "Commit")


def test_reading_must_be_verses_not_a_whole_chapter():
    with pytest.raises(ValidationError):
        guide(read_refs=["Mark 10"]).validate()
    guide(read_refs=["Mark 10:2-9"]).validate()


def test_at_most_two_reading_sections():
    guide(read_refs=["Mark 10:2-9", "Mark 10:13-16"]).validate()
    with pytest.raises(ValidationError):
        guide(read_refs=["Mark 10:2-9", "Mark 10:13-16", "Mark 10:17-22"]).validate()


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
