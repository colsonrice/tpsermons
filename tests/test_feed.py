import pathlib
from tpsermons.feed import parse_feed

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "podcast.xml"
XML = FIXTURE.read_text(encoding="utf-8")


def test_parses_episodes_with_required_fields():
    eps = parse_feed(XML)
    assert eps, "expected at least one episode"
    e = eps[0]
    assert e.guid
    assert e.mp3_url.endswith(".mp3")
    assert e.pub_date.year == 2026


def test_episodes_are_newest_first():
    eps = parse_feed(XML)
    dates = [e.pub_date for e in eps]
    assert dates == sorted(dates, reverse=True)


def test_every_returned_episode_is_a_sermon_with_a_passage():
    # Clips and podcast episodes must be filtered out entirely rather than
    # processed with empty fields (spec: Data model).
    for e in parse_feed(XML):
        assert e.passage is not None
        assert e.series is not None


def test_known_episode_is_parsed_correctly():
    eps = parse_feed(XML)
    pop = [e for e in eps if e.title == "Presence Over Position"][0]
    assert pop.series == "The Urgent Kingdom"
    assert pop.passage == "Mark 9:30-50"
    assert pop.slug == "presence-over-position"


def test_curly_apostrophe_title_does_not_crash_parsing():
    # The real feed contains typographic apostrophes; parsing must survive them.
    assert parse_feed(XML) is not None
