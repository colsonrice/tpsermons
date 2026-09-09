from tests.fixtures import make_guide
from tpsermons.mail import MailConfig, render_email

URL = "https://colsonrice.github.io/tpsermons/guides/x.html"
SHEET = "https://colsonrice.github.io/tpsermons/guides/x-reflection.html"


def test_subject_names_the_guide_and_passage():
    subject, _h, _t = render_email(make_guide(), URL)
    assert "Presence Over Position" in subject and "Mark 9:30-50" in subject


def test_html_contains_the_whole_leader_guide():
    g = make_guide()
    _s, html, _t = render_email(g, URL, SHEET)
    for needed in (g.goal, g.leader_notes[0], g.icebreakers[0].question,
                   g.sections[0].questions[0], g.closing_go_around,
                   g.cheat_sheet[0].response, g.key_themes[0]):
        assert needed in html, needed


def test_questions_are_numbered_continuously():
    _s, html, _t = render_email(make_guide(), URL)
    assert ">12.</span>" in html


def test_links_to_both_documents():
    _s, html, _t = render_email(make_guide(), URL, SHEET)
    assert URL in html and SHEET in html


def test_inline_styles_because_gmail_strips_stylesheets():
    _s, html, _t = render_email(make_guide(), URL)
    assert "<style" not in html and 'style="' in html


def test_plain_text_alternative_is_provided():
    _s, _h, text = render_email(make_guide(), URL)
    assert "CHEAT SHEET" in text and URL in text and "<" not in text


def test_escapes_html_in_content():
    _s, html, _t = render_email(make_guide(title="Faith & Doubt <today>"), URL)
    assert "Faith &amp; Doubt &lt;today&gt;" in html


def test_config_absent_when_env_incomplete():
    assert MailConfig.from_env({}) is None
    assert MailConfig.from_env({"SMTP_USER": "a@b.c"}) is None


def test_config_parses_multiple_recipients():
    cfg = MailConfig.from_env({"SMTP_USER": "me@gmail.com", "SMTP_PASSWORD": "pw",
                               "MAIL_TO": "a@x.com, b@y.com"})
    assert cfg.to == ["a@x.com", "b@y.com"]
    assert cfg.host == "smtp.gmail.com" and cfg.port == 587


def test_config_allows_overriding_the_provider():
    cfg = MailConfig.from_env({"SMTP_USER": "u", "SMTP_PASSWORD": "p",
                               "MAIL_TO": "a@x.com", "SMTP_HOST": "smtp.fastmail.com",
                               "SMTP_PORT": "465"})
    assert cfg.host == "smtp.fastmail.com" and cfg.port == 465
