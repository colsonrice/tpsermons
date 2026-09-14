from tests.fixtures import make_guide, make_new_guide
from tpsermons.mail import MailConfig, render_email

URL = "https://colsonrice.github.io/tpsermons/guides/x.html"
SHEET = "https://colsonrice.github.io/tpsermons/guides/x-reflection.html"


def test_subject_leads_with_the_guide_title():
    subject, _h, _t = render_email(make_guide(), URL)
    assert subject.startswith("Position or Presence") and "Mark 9:30-50" in subject


def test_classic_email_carries_leader_notes():
    g = make_guide()
    _s, html, _t = render_email(g, URL, SHEET)
    assert g.leader_notes[0][:40] in html and g.sections[0].questions[0].ask in html


def test_new_email_carries_thesis_get_honest_and_carry():
    g = make_new_guide()
    _s, html, text = render_email(g, URL, SHEET)
    for needed in (g.thesis, g.obstacle, g.carry, "MUST ASK"):
        assert needed in html, needed
    assert "GET HONEST" in text


def test_links_both_documents_and_uses_inline_styles():
    _s, html, text = render_email(make_new_guide(), URL, SHEET)
    assert URL in html and SHEET in html and "<style" not in html and URL in text


def test_config_parsing():
    assert MailConfig.from_env({}) is None
    cfg = MailConfig.from_env({"SMTP_USER": "me@gmail.com", "SMTP_PASSWORD": "pw",
                               "MAIL_TO": "a@x.com, b@y.com"})
    assert cfg.to == ["a@x.com", "b@y.com"] and cfg.port == 587
