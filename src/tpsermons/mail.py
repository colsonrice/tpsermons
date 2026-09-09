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


def render_email(guide, url: str):
    """Return (subject, html, plain_text) for one guide."""
    refs = " · ".join(guide.read_refs)
    subject = "%s — %s" % (guide.title, refs)

    meta = " · ".join(b for b in (guide.series, guide.passage, guide.speaker) if b)

    parts = [
        "<div style=\"background:%s;padding:26px 20px\">" % PAPER,
        "<div style=\"max-width:600px;margin:0 auto\">",
        "<p style=\"margin:0 0 6px;font:600 12px/1.4 %s;letter-spacing:.16em;"
        "text-transform:uppercase;color:%s\">This week's guide</p>" % (_SERIF, CLAY),
        "<h1 style=\"margin:0 0 8px;font:400 30px/1.15 %s;color:%s\">%s</h1>"
        % (_SERIF, INK, _e(guide.title)),
        _p(meta, "14px", FAINT),
    ]

    parts.append(_label("Before you start"))
    for n in guide.leader_notes:
        parts.append(_p("— " + n, "15px", SOFT))

    parts.append(_label("Open"))
    parts.append(_p(guide.opener, "19px"))

    parts.append(_label("Read"))
    parts.append(_p(guide.context, "16px", SOFT))
    parts.append("<p style=\"margin:0 0 14px;font:400 18px/1.5 %s;color:%s;"
                 "border-left:3px solid %s;padding-left:12px\">%s</p>"
                 % (_SERIF, SAGE, SAGE, _e(refs)))
    parts.append(_p(guide.read_aloud, "16px", SOFT, "font-style:italic;"))
    parts.append(_p(guide.observation, "19px"))

    parts.append(_label("Discuss"))
    for i, b in enumerate(guide.discuss, 1):
        parts.append("<p style=\"margin:22px 0 6px;font:600 12px/1.4 %s;"
                     "letter-spacing:.1em;text-transform:uppercase;color:%s\">%d. %s</p>"
                     % (_SERIF, FAINT, i, _e(b.heading)))
        parts.append(_p(b.question, "19px"))
        # Probes render open: <details> is unsupported in most mail clients.
        for probe in b.probes:
            parts.append(_p("· " + probe, "15px", SOFT, "margin-left:14px;"))

    parts.append(_label("Get honest", "#8A3822"))
    parts.append(_p(guide.obstacle, "20px"))

    parts.append(_label("Commit", SAGE))
    parts.append(_p(guide.commit, "17px"))
    parts.append(_p("Next week we ask: " + guide.carry, "15px", SOFT))

    parts.append("<p style=\"margin:30px 0 0;padding-top:16px;border-top:1px solid %s;"
                 "font:400 14px/1.6 %s\"><a href=\"%s\" style=\"color:%s\">"
                 "Open this guide on the web</a></p>" % (RULE, _SERIF, _e(url), CLAY))
    parts.append(_p("Generated from the sermon. Sermon content belongs to Traders "
                    "Point Christian Church; this is a study aid, not a transcript.",
                    "12px", FAINT))
    parts.append("</div></div>")

    text_lines = [
        guide.title, meta, "", "BEFORE YOU START",
        *["- %s" % n for n in guide.leader_notes],
        "", "OPEN", guide.opener,
        "", "READ", guide.context, refs, guide.read_aloud, guide.observation,
        "", "DISCUSS",
    ]
    for i, b in enumerate(guide.discuss, 1):
        text_lines += ["", "%d. %s" % (i, b.heading), b.question]
        text_lines += ["   - %s" % p for p in b.probes]
    text_lines += ["", "GET HONEST", guide.obstacle,
                   "", "COMMIT", guide.commit,
                   "Next week we ask: " + guide.carry, "", url]

    return subject, "".join(parts), "\n".join(text_lines)


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
