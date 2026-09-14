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
    """Return (subject, html, plain_text) for one edition of the guide."""
    from .render import preacher_line
    subject = "%s: %s%s" % (guide.guide_title, guide.title,
                            " (%s)" % guide.passage if guide.passage else "")
    meta = " · ".join(b for b in (guide.series, guide.passage, preacher_line(guide)) if b)
    new = guide.mode == "new"

    P = ["<div style=\"background:%s;padding:26px 20px\">" % PAPER,
         "<div style=\"max-width:600px;margin:0 auto\">",
         "<p style=\"margin:0 0 6px;font:600 12px/1.4 %s;letter-spacing:.16em;"
         "text-transform:uppercase;color:%s\">This week's guide</p>" % (_SERIF, CLAY),
         "<h1 style=\"margin:0 0 6px;font:400 30px/1.15 %s;color:%s\">%s</h1>"
         % (_SERIF, INK, _e(guide.guide_title)),
         _p(guide.title, "16px", SOFT), _p(meta, "14px", FAINT),
         _p(guide.goal, "16px", SOFT, "font-style:italic;")]
    T = [guide.guide_title, guide.title, meta, "", guide.goal]

    if new:
        P += [_label("The one sentence"), _p(guide.thesis, "18px")]
        P += [_label("The sermon's moves")] + [_p("%d. %s" % (i, o), "15px", SOFT)
                                               for i, o in enumerate(guide.outline, 1)]
        if guide.sensitivities:
            P += [_label("Handle with care")] + [_p(x, "15px", SOFT)
                                                 for x in guide.sensitivities]
        T += ["", "THE ONE SENTENCE", guide.thesis, "", "MOVES"] + guide.outline
    else:
        P += [_label("Before you begin")] + [_p(x, "15px", SOFT) for x in guide.leader_notes]
        T += ["", "BEFORE YOU BEGIN"] + guide.leader_notes

    P += [_label("Opening")]
    if new and guide.read_refs:
        P.append(_p("Read: " + " · ".join(guide.read_refs), "16px", SAGE))
    P.append(_p(guide.scripture_instructions, "16px"))
    T += ["", "OPENING", guide.scripture_instructions]
    for i in guide.icebreakers:
        P.append(_p("%s (%s). %s" % (i.label, i.fits, i.question), "16px"))
        T.append("%s (%s). %s" % (i.label, i.fits, i.question))

    n = 0
    for sec in guide.sections:
        P.append(_label(sec.title))
        T += ["", sec.title.upper()]
        if new and sec.say:
            P.append(_p("Say: " + sec.say, "15px", SAGE))
        else:
            P.append(_p(sec.setup, "15px", SOFT))
        for q in sec.questions:
            n += 1
            if q.lead:
                P.append(_p(q.lead, "14px", SOFT, "margin:0 0 4px;"))
            P.append("<p style=\"margin:0 0 14px;font:600 18px/1.45 %s;color:%s\">"
                     "<span style=\"color:%s\">%d.</span> %s%s</p>"
                     % (_SERIF, INK, CLAY, n, _e(q.ask),
                        " <span style=\"color:%s;font-size:12px\">MUST ASK</span>" % CLAY
                        if q.star else ""))
            T.append("%d. %s" % (n, q.ask))

    if new and guide.obstacle:
        P += [_label("Get honest"), _p(guide.obstacle, "19px")]
        T += ["", "GET HONEST", guide.obstacle]
    P += [_label("Closing", SAGE), _p(guide.closing_go_around, "16px"),
          _p("Prayer: " + guide.prayer, "15px", SOFT)]
    T += ["", "CLOSING", guide.closing_go_around, "Prayer: " + guide.prayer]
    if new and guide.carry:
        P.append(_p("Next week we ask: " + guide.carry, "15px", SOFT))
        T.append("Next week we ask: " + guide.carry)

    links = "<a href=\"%s\" style=\"color:%s\">Open the guide</a>" % (_e(url), CLAY)
    if sheet_url:
        links += (" &nbsp;·&nbsp; <a href=\"%s\" style=\"color:%s\">Reflection sheet"
                  "</a>" % (_e(sheet_url), CLAY))
    P.append("<p style=\"margin:30px 0 0;padding-top:16px;border-top:1px solid %s;"
             "font:400 14px/1.6 %s\">%s</p>" % (RULE, _SERIF, links))
    P.append(_p("Generated from the sermon. Sermon content belongs to Traders Point "
                "Christian Church; this is a study aid, not a transcript.", "12px", FAINT))
    P.append("</div></div>")
    T += ["", url] + ([sheet_url] if sheet_url else [])
    return subject, "".join(P), "\n".join(T)


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
