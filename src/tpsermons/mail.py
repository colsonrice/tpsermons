"""Email delivery of the weekly guide.

The whole guide goes in the body, not just a link: the leader should be able to
read it on a phone without clicking through. That constrains the markup --
styles must be inline (Gmail strips <style>) and <details> cannot be used
(unsupported in most clients), so probes render open.

Provider-agnostic SMTP. Gmail works with an app password; anything else works
by overriding SMTP_HOST and SMTP_PORT.
"""
from __future__ import annotations

import html as _html
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List, Optional

INK = "#1A1512"
SOFT = "#5D534B"
FAINT = "#938779"
CLAY = "#A8442A"
SAGE = "#6A7355"
PAPER = "#FAF6EF"
RULE = "#E6DCCB"

_SERIF = "Georgia,'Iowan Old Style','Times New Roman',serif"


@dataclass
class MailConfig:
    user: str
    password: str
    to: List[str]
    host: str = "smtp.gmail.com"
    port: int = 587
    sender: Optional[str] = None

    @classmethod
    def from_env(cls, env) -> Optional["MailConfig"]:
        """Build config, or None when mail is not configured.

        Absent configuration is not an error -- the guide still publishes.
        """
        user = (env.get("SMTP_USER") or "").strip()
        password = (env.get("SMTP_PASSWORD") or "").strip()
        raw_to = (env.get("MAIL_TO") or "").strip()
        if not (user and password and raw_to):
            return None
        recipients = [a.strip() for a in raw_to.replace(";", ",").split(",") if a.strip()]
        if not recipients:
            return None
        return cls(
            user=user, password=password, to=recipients,
            host=(env.get("SMTP_HOST") or "smtp.gmail.com").strip(),
            port=int(env.get("SMTP_PORT") or 587),
            sender=(env.get("MAIL_FROM") or "").strip() or user,
        )


def _e(text) -> str:
    return _html.escape(str(text or ""))


def _p(text, size="16px", color=INK, style="") -> str:
    return ("<p style=\"margin:0 0 14px;font:%s/1.6 %s;color:%s;%s\">%s</p>"
            % (size, _SERIF, color, style, _e(text)))


def _label(text, color=CLAY) -> str:
    return ("<p style=\"margin:26px 0 10px;font:600 12px/1.4 %s;letter-spacing:.16em;"
            "text-transform:uppercase;color:%s;border-bottom:1px solid %s;"
            "padding-bottom:6px\">%s</p>" % (_SERIF, color, RULE, _e(text)))


def render_email(guide, url: str, sheet_url: str = ""):
    """Return (subject, html, plain_text) for the leader guide."""
    subject = "%s%s" % (guide.title, " — %s" % guide.passage if guide.passage else "")
    meta = " · ".join(b for b in (guide.series, guide.passage, guide.speaker) if b)

    parts = [
        "<div style=\"background:%s;padding:26px 20px\">" % PAPER,
        "<div style=\"max-width:600px;margin:0 auto\">",
        "<p style=\"margin:0 0 6px;font:600 12px/1.4 %s;letter-spacing:.16em;"
        "text-transform:uppercase;color:%s\">This week's guide</p>" % (_SERIF, CLAY),
        "<h1 style=\"margin:0 0 8px;font:400 30px/1.15 %s;color:%s\">%s</h1>"
        % (_SERIF, INK, _e(guide.title)),
        _p(meta, "14px", FAINT),
        _p(guide.goal, "16px", SOFT, "font-style:italic;"),
    ]

    parts.append(_label("Before you begin"))
    for note in guide.leader_notes:
        parts.append(_p(note, "15px", SOFT))

    parts.append(_label("Opening"))
    parts.append(_p(guide.scripture_instructions, "16px"))
    for ice in guide.icebreakers:
        parts.append(_p("%s. %s" % (ice.label, ice.question), "16px"))
        parts.append(_p(ice.fits, "13px", FAINT, "margin:-8px 0 12px 14px;"))

    n = 0
    for sec in guide.sections:
        parts.append(_label(sec.title))
        parts.append(_p(sec.setup, "15px", SOFT))
        for q in sec.questions:
            n += 1
            parts.append("<p style=\"margin:0 0 12px;font:600 18px/1.45 %s;color:%s\">"
                         "<span style=\"color:%s\">%d.</span> %s</p>"
                         % (_SERIF, INK, CLAY, n, _e(q)))

    parts.append(_label("Closing", SAGE))
    parts.append(_p(guide.closing_go_around, "16px"))
    parts.append(_p(guide.prayer, "15px", SOFT))

    parts.append(_label("Cheat sheet", FAINT))
    for row in guide.cheat_sheet:
        parts.append(_p("%s: %s" % (row.dynamic, row.response), "14px", SOFT))

    parts.append(_label("Key themes", FAINT))
    for theme in guide.key_themes:
        parts.append(_p("· " + theme, "14px", SOFT))

    links = "<a href=\"%s\" style=\"color:%s\">Open the guide</a>" % (_e(url), CLAY)
    if sheet_url:
        links += " &nbsp;·&nbsp; <a href=\"%s\" style=\"color:%s\">Reflection sheet</a>" \
                 % (_e(sheet_url), CLAY)
    parts.append("<p style=\"margin:30px 0 0;padding-top:16px;border-top:1px solid %s;"
                 "font:400 14px/1.6 %s\">%s</p>" % (RULE, _SERIF, links))
    parts.append(_p("Generated from the sermon. Sermon content belongs to Traders "
                    "Point Christian Church; this is a study aid, not a transcript.",
                    "12px", FAINT))
    parts.append("</div></div>")

    text = [guide.title, meta, "", guide.goal, "", "BEFORE YOU BEGIN"]
    text += guide.leader_notes
    text += ["", "OPENING", guide.scripture_instructions]
    text += ["%s. %s (%s)" % (i.label, i.question, i.fits) for i in guide.icebreakers]
    n = 0
    for sec in guide.sections:
        text += ["", sec.title.upper(), sec.setup]
        for q in sec.questions:
            n += 1
            text.append("%d. %s" % (n, q))
    text += ["", "CLOSING", guide.closing_go_around, guide.prayer]
    text += ["", "CHEAT SHEET"]
    text += ["%s: %s" % (r.dynamic, r.response) for r in guide.cheat_sheet]
    text += ["", "KEY THEMES"] + ["- %s" % t for t in guide.key_themes]
    text += ["", url]
    if sheet_url:
        text.append(sheet_url)
    return subject, "".join(parts), "\n".join(text)


def send(subject: str, body_html: str, body_text: str, cfg: MailConfig) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.sender or cfg.user
    msg["To"] = ", ".join(cfg.to)
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    context = ssl.create_default_context()
    if cfg.port == 465:
        with smtplib.SMTP_SSL(cfg.host, cfg.port, context=context, timeout=30) as s:
            s.login(cfg.user, cfg.password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as s:
            s.starttls(context=context)
            s.login(cfg.user, cfg.password)
            s.send_message(msg)
