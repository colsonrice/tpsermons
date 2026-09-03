from tpsermons.state import State


def test_seed_marks_all_but_the_most_recent(tmp_path):
    # Bootstrap must leave exactly one episode pending, or the first run would
    # process the whole 224-episode back catalogue.
    st = State(tmp_path / "state.json")
    st.seed(["newest", "older", "oldest"])
    assert not st.is_processed("newest")
    assert st.is_processed("older")
    assert st.is_processed("oldest")


def test_seed_on_empty_feed_is_safe(tmp_path):
    State(tmp_path / "state.json").seed([])


def test_pending_returns_oldest_first(tmp_path):
    # A backlog after failed runs must catch up in order, not drop sermons.
    st = State(tmp_path / "state.json")
    st.mark("c")
    pending = st.pending(["a", "b", "c"])          # newest-first input
    assert pending == ["b", "a"]                    # oldest-first output


def test_state_persists_across_instances(tmp_path):
    path = tmp_path / "state.json"
    State(path).mark("x")
    assert State(path).is_processed("x")


def test_missing_state_file_is_treated_as_empty(tmp_path):
    assert State(tmp_path / "nope.json").pending(["a"]) == ["a"]
