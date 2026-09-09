import pytest

from tpsermons.mail import MailConfig, render_email
from tests.test_render import guide

URL = "https://colsonrice.github.io/tpsermons/guides/x.html"


def test_subject_names_the_guide_and_the_reading():
    subject, _html, _text = render_email(guide(), URL)
    assert "Presence Over Position" in subject
    assert "Mark 9:33-37" in subject


def test_html_contains_the_whole_guide_so_no_click_is_needed():
    _s, html, _t = render_email(guide(), URL)
    for needed in ("Heading 0", "Where has that shown up for you?",
                   "When did you last want a title more than the work?",
                   "What will realistically stop you this week?",
                   "Next week we ask how that conversation went."):
        assert needed in html, needed


def test_html_uses_inline_styles_because_gmail_strips_stylesheets():
    _s, html, _t = render_email(guide(), URL)
    assert "<style" not in html
    assert 'style="' in html


def test_probes_are_visible_in_email_not_hidden_behind_a_toggle():
    # <details> is unsupported in most mail clients; probes must render open.
    _s, html, _t = render_email(guide(), URL)
    assert "<details" not in html
    assert "Probe A" in html


def test_plain_text_alternative_is_provided():
    _s, _h, text = render_email(guide(), URL)
    assert "Probe A" in text
    assert "<" not in text.replace("<br>", "")
    assert URL in text


def test_escapes_html_in_guide_content():
    _s, html, _t = render_email(guide(title="Faith & Doubt <today>"), URL)
    assert "Faith &amp; Doubt &lt;today&gt;" in html


def test_config_absent_when_env_incomplete():
    assert MailConfig.from_env({}) is None
    assert MailConfig.from_env({"SMTP_USER": "a@b.c"}) is None


def test_config_parses_multiple_recipients():
    cfg = MailConfig.from_env({
        "SMTP_USER": "me@gmail.com", "SMTP_PASSWORD": "pw",
        "MAIL_TO": "a@x.com, b@y.com",
    })
    assert cfg.to == ["a@x.com", "b@y.com"]
    assert cfg.host == "smtp.gmail.com" and cfg.port == 587


def test_config_allows_overriding_the_provider():
    cfg = MailConfig.from_env({
        "SMTP_USER": "u", "SMTP_PASSWORD": "p", "MAIL_TO": "a@x.com",
        "SMTP_HOST": "smtp.fastmail.com", "SMTP_PORT": "465",
    })
    assert cfg.host == "smtp.fastmail.com" and cfg.port == 465
