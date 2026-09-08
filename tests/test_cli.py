import json
from datetime import datetime, timezone

from tpsermons.cli import Deps, run
from tpsermons.models import DiscussBlock, Episode, Guide

def ep(guid, day, title="Sermon %s"):
    return Episode(guid=guid, title=title % guid,
                   pub_date=datetime(2026, 8, day, tzinfo=timezone.utc),
                   mp3_url="https://x/%s.mp3" % guid, series="S", passage="Mark 9")


def fake_guide(episode, **_):
    return Guide(
        title=episode.title, series="S", speaker=None,
        date=episode.pub_date.strftime("%Y-%m-%d"), passage="Mark 9",
        links={"tpcc": "https://tpcc.org/messages/x"},
        leader_notes=["Talk less than a quarter of the night.",
                      "Go easy if this one lands hard."],
        opener="When did you last change your mind?",
        context=" ".join(["word"] * 30),
        read_aloud="Read Mark 9 aloud; listen for the argument.",
        observation="What did Jesus actually say?",
        discuss=[DiscussBlock("H%d" % i, "Where has that shown up for you?",
                              ["a", "b"]) for i in range(3)],
        obstacle="What will stop you before next Thursday?",
        commit=" ".join(["word"] * 40),
        carry="Next week we ask how it went.",
        source="youtube_captions")


def deps(episodes):
    return Deps(
        episodes=lambda: episodes,
        resolve=lambda e: ("text", "youtube_captions"),
        links=lambda e: ({"tpcc": "https://tpcc.org/messages/x"}, None),
        generate=fake_guide,
    )


def test_no_new_episode_is_a_clean_noop(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"processed": ["a"]}))
    written = run(deps([ep("a", 30)]), out_dir=tmp_path / "guides",
                  state_path=tmp_path / "state.json")
    assert written == []          # nothing produced, and no exception raised


def test_multiple_pending_are_processed_oldest_first(tmp_path):
    episodes = [ep("new", 30), ep("mid", 23), ep("old", 16)]
    written = run(deps(episodes), out_dir=tmp_path / "guides",
                  state_path=tmp_path / "state.json")
    assert len(written) == 3
    assert [p.name[:10] for p in written] == ["2026-08-16", "2026-08-23", "2026-08-30"]


def test_episode_flag_bypasses_the_state_gate(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"processed": ["a"]}))
    written = run(deps([ep("a", 30)]), out_dir=tmp_path / "guides",
                  state_path=tmp_path / "state.json", episode="a")
    assert len(written) == 1


def test_episode_flag_refuses_to_overwrite_without_force(tmp_path):
    out = tmp_path / "guides"
    st = tmp_path / "state.json"
    run(deps([ep("a", 30)]), out_dir=out, state_path=st, episode="a")
    again = run(deps([ep("a", 30)]), out_dir=out, state_path=st, episode="a")
    assert again == []            # Decision 2: no silent regeneration


def test_force_allows_deliberate_overwrite(tmp_path):
    out = tmp_path / "guides"
    st = tmp_path / "state.json"
    run(deps([ep("a", 30)]), out_dir=out, state_path=st, episode="a")
    again = run(deps([ep("a", 30)]), out_dir=out, state_path=st, episode="a", force=True)
    assert len(again) == 1
