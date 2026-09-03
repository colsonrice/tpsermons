from tpsermons.titles import parse_title, is_sermon_title


def test_parses_three_segment_title():
    p = parse_title("Presence Over Position | The Urgent Kingdom | Mark 9:30-50")
    assert p.title == "Presence Over Position"
    assert p.series == "The Urgent Kingdom"
    assert p.passage == "Mark 9:30-50"


def test_full_gathering_cut_is_not_a_sermon():
    # The Full Gathering cut adds ~3000 words of worship and announcements.
    assert not is_sermon_title("Enough | The Urgent Kingdom | Mark 8:1-13 | Full Gathering")
    assert is_sermon_title("Enough | The Urgent Kingdom | Mark 8:1-13")


def test_clips_and_podcast_episodes_are_not_sermons():
    assert not is_sermon_title("Does God send people to hell?")
    assert not is_sermon_title("Have We Lost the Fear of God? | Taking Ground Podcast")


def test_unparseable_title_yields_none_fields_rather_than_raising():
    p = parse_title("Some Talk")
    assert p.title == "Some Talk"
    assert p.series is None
    assert p.passage is None


def test_matching_is_whitespace_and_case_insensitive():
    from tpsermons.titles import normalize
    a = "Enough |  The Urgent Kingdom | Mark 8:1-13"
    b = "enough | the urgent kingdom | mark 8:1-13"
    assert normalize(a) == normalize(b)
