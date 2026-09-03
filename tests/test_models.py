import pytest
from tpsermons.models import DiscussBlock, Guide, ValidationError


def blocks(n=3, q=2):
    return [DiscussBlock(heading="H%d" % i, questions=["Q%d" % j for j in range(q)])
            for i in range(n)]


def guide(**kw):
    base = dict(
        title="T", series="S", speaker=None, date="2026-08-30", passage="Mark 9:30-50",
        links={"tpcc": "https://tpcc.org/messages/x"},
        recap=" ".join(["word"] * 80), discuss=blocks(),
        take_action=" ".join(["word"] * 60), reflections=["a", "b", "c"],
        source="youtube_captions",
    )
    base.update(kw)
    return Guide(**base)


def test_valid_guide_passes():
    guide().validate()


@pytest.mark.parametrize("kw,why", [
    (dict(discuss=blocks(n=2)), "too few discuss blocks"),
    (dict(discuss=blocks(n=4)), "too many discuss blocks"),
    (dict(discuss=blocks(q=1)), "too few questions in a block"),
    (dict(discuss=blocks(q=4)), "too many questions in a block"),
    (dict(reflections=["a", "b"]), "wrong reflection count"),
    (dict(recap="too short"), "recap under word floor"),
    (dict(recap=" ".join(["w"] * 200)), "recap over word ceiling"),
    (dict(take_action="short"), "take_action under floor"),
])
def test_invalid_shapes_rejected(kw, why):
    with pytest.raises(ValidationError):
        guide(**kw).validate()


def test_placeholder_tokens_rejected():
    for token in ["TODO", "TBD", "FIXME", "Lorem"]:
        with pytest.raises(ValidationError):
            guide(recap=" ".join(["word"] * 79 + [token])).validate()
    with pytest.raises(ValidationError):
        guide(take_action=" ".join(["word"] * 59) + " [insert application here]").validate()


def test_ellipsis_and_asr_markers_are_not_placeholders():
    # Deliberate carve-out: ellipses occur in legitimate quotation and ASR
    # emits bracketed markers. Neither may fail a valid guide.
    guide(recap=" ".join(["word"] * 78) + " he said ... [inaudible]").validate()


def test_tpcc_link_is_required():
    with pytest.raises(ValidationError):
        guide(links={"youtube": "https://youtu.be/x"}).validate()
