"""Rendering: Guide -> markdown, HTML, and the participant reflection sheet.

Two documents come out of every guide. The leader guide carries all the
scaffolding: notes, setups, timings, the cheat sheet. The reflection sheet
carries the same questions in the first person and nothing else, because
pastoral flags must never reach the participants.
"""
from __future__ import annotations

import html
import re

from .models import CheatRow, Guide, Icebreaker, Section

LINK_LABELS = [("tpcc", "Message page"), ("youtube", "Watch"), ("podcast", "Listen")]

_FONTS = (
    "<link rel='preconnect' href='https://fonts.googleapis.com'>"
    "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
    "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
    "family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&"
    "family=Newsreader:ital,opsz,wght@0,6..72,300..700;1,6..72,300..700&display=swap'>"
)
_ICON = (
    "<link rel='icon' href=\"data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='6' fill='%23A8442A'/%3E"
    "%3Ctext x='16' y='23' font-size='19' font-family='Georgia,serif' "
    "text-anchor='middle' fill='%23FAF6EF'%3EG%3C/text%3E%3C/svg%3E\">"
)

ICEBREAKER_ORDER = ("A", "B", "C")


def _e(text):
    return html.escape(str(text or ""))


def _doc(title, depth, body):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta name='color-scheme' content='light dark'>"
            "<title>%s</title>%s%s<link rel='stylesheet' href='%sassets/style.css'>"
            "</head><body>%s</body></html>"
            % (_e(title), _FONTS, _ICON, depth, body))


def _pretty_date(iso):
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except (ValueError, AttributeError):
        return iso
    return "%s %d, %d" % (("January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November",
                           "December")[m - 1], d, y)


def _short_date(iso):
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except (ValueError, AttributeError):
        return iso
    return "%s %d" % (("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                       "Sep", "Oct", "Nov", "Dec")[m - 1], d)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "message"


def guide_filename(guide, ext="md", kind="guide"):
    stem = "%s-%s" % (guide.date, slugify(guide.title))
    if kind == "reflection":
        stem += "-reflection"
    return "%s.%s" % (stem, ext)


# --- serialisation ----------------------------------------------------------

def guide_to_dict(g):
    return {
        "title": g.title, "series": g.series, "speaker": g.speaker, "date": g.date,
        "passage": g.passage, "links": g.links, "source": g.source,
        "goal": g.goal, "leader_notes": list(g.leader_notes),
        "scripture_instructions": g.scripture_instructions,
        "icebreakers": [{"label": i.label, "question": i.question, "fits": i.fits}
                        for i in g.icebreakers],
        "sections": [{"title": s.title, "setup": s.setup,
                      "questions": list(s.questions),
                      "reflection_questions": list(s.reflection_questions)}
                     for s in g.sections],
        "closing_go_around": g.closing_go_around, "prayer": g.prayer,
        "cheat_sheet": [{"dynamic": c.dynamic, "response": c.response}
                        for c in g.cheat_sheet],
        "key_themes": list(g.key_themes), "commitment_prompt": g.commitment_prompt,
    }


def guide_from_dict(d):
    return Guide(
        title=d["title"], series=d.get("series"), speaker=d.get("speaker"),
        date=d["date"], passage=d.get("passage"), links=d.get("links", {}),
        goal=d["goal"], leader_notes=d["leader_notes"],
        scripture_instructions=d["scripture_instructions"],
        icebreakers=[Icebreaker(i["label"], i["question"], i["fits"])
                     for i in d["icebreakers"]],
        sections=[Section(s["title"], s["setup"], s["questions"],
                          s["reflection_questions"]) for s in d["sections"]],
        closing_go_around=d["closing_go_around"], prayer=d["prayer"],
        cheat_sheet=[CheatRow(c["dynamic"], c["response"]) for c in d["cheat_sheet"]],
        key_themes=d["key_themes"], commitment_prompt=d["commitment_prompt"],
        source=d.get("source", ""))


# --- markdown ---------------------------------------------------------------

def _front_matter(g, kind):
    L = ["---", "title: %s" % g.title, "date: %s" % g.date, "kind: %s" % kind]
    for field in ("series", "passage", "speaker"):
        if getattr(g, field):
            L.append("%s: %s" % (field, getattr(g, field)))
    return L + ["source: %s" % g.source, "---", ""]


def render_markdown(g):
    """The leader guide."""
    L = _front_matter(g, "guide")
    L += ["# %s" % g.title, ""]
    meta = [b for b in (g.series, g.passage, g.speaker) if b]
    if meta:
        L += [" · ".join(meta), ""]
    links = ["[%s](%s)" % (lbl, g.links[k]) for k, lbl in LINK_LABELS if g.links.get(k)]
    if links:
        L += [" · ".join(links), ""]

    L += ["**At a glance.** About 60 minutes, 10 to 12 men, Bibles and a pen. "
          "%s" % g.goal, "", "---", "", "## Before You Begin", ""]
    L += [p + "\n" for p in g.leader_notes]
    L += ["---", "", "## Opening", "", g.scripture_instructions, "",
          "Pick one icebreaker:", ""]
    for ice in g.icebreakers:
        L += ["**%s. %s**" % (ice.label, ice.question), "", "*%s*" % ice.fits, ""]
    L += ["---", ""]

    for sec in g.sections:
        L += ["## %s" % sec.title, "", sec.setup, ""]
        for q in sec.questions:
            L += ["**%s**" % q, ""]
        L += ["---", ""]

    L += ["## Closing and Application", "", g.closing_go_around, "", g.prayer, "",
          "---", "", "## Facilitator Cheat Sheet", "",
          "| If this happens | Try this |", "| --- | --- |"]
    L += ["| %s | %s |" % (c.dynamic, c.response) for c in g.cheat_sheet]
    L += ["", "---", "", "## Key Themes to Reinforce", ""]
    L += ["- %s" % t for t in g.key_themes]
    L += ["", "---", "",
          "*Generated from the sermon (%s). Sermon content belongs to Traders "
          "Point Christian Church; this is a study aid, not a transcript.*" % g.source, ""]
    return "\n".join(L)


def render_reflection_markdown(g):
    """The participant sheet: questions only, first person, no scaffolding."""
    L = _front_matter(g, "reflection")
    L += ["# %s" % g.title, ""]
    meta = [b for b in (g.series, g.passage, g.speaker) if b]
    if meta:
        L += [" · ".join(meta), "", "---", ""]
    for sec in g.sections:
        L += ["## %s" % sec.title, ""]
        for q in sec.reflection_questions:
            L += ["**%s**" % q, "", "", ""]
    L += ["---", "", "## This Week", "", g.commitment_prompt, "", "", ""]
    return "\n".join(L)


# --- HTML -------------------------------------------------------------------

def _meta_line(date=None, passage=None, speaker=None):
    bits = []
    if date:
        bits.append("<span>%s</span>" % _e(_pretty_date(date)))
    if speaker:
        bits.append("<span>%s</span>" % _e(speaker))
    if passage:
        bits.append("<span class='passage'>%s</span>" % _e(passage))
    return "<div class='meta'>%s</div>" % "".join(bits)


def _header(g, subtitle=None, sheet_link=None):
    eyebrow = "<p class='eyebrow'>%s</p>" % _e(g.series) if g.series else ""
    links = "".join("<a href=\"%s\">%s</a>" % (g.links[k], _e(lbl))
                    for k, lbl in LINK_LABELS if g.links.get(k))
    if sheet_link:
        links += "<a href=\"%s\" class='alt'>%s</a>" % (sheet_link[0], _e(sheet_link[1]))
    sub = "<p class='subtitle'>%s</p>" % _e(subtitle) if subtitle else ""
    return ("<header class='guide-head rise'>%s<h1>%s</h1>%s%s"
            "<div class='links'>%s</div></header>"
            % (eyebrow, _e(g.title), sub, _meta_line(g.date, g.passage, g.speaker), links))


def render_guide_page(g):
    """The leader guide."""
    glance = ("<div class='glance rise'><dl>"
              "<div><dt>Runs</dt><dd>About 60 minutes</dd></div>"
              "<div><dt>Group</dt><dd>10 to 12 men</dd></div>"
              "<div><dt>Bring</dt><dd>Bibles, a pen</dd></div>"
              "</dl><p class='goal'>%s</p></div>" % _e(g.goal))

    notes = ("<section class='seg leader-notes rise'><div class='seg-head'>"
             "<h2>Before you begin</h2></div>%s</section>"
             % "".join("<p>%s</p>" % _e(n) for n in g.leader_notes))

    ice = "".join(
        "<div class='ice'><div class='ice-label'>%s</div><div>"
        "<p class='ask'>%s</p><p class='fits'>%s</p></div></div>"
        % (_e(i.label), _e(i.question), _e(i.fits)) for i in g.icebreakers)
    opening = ("<section class='seg rise'><div class='seg-head'><h2>Opening</h2></div>"
               "<p class='read-aloud'>%s</p><p class='instruction'>Pick one</p>%s</section>"
               % (_e(g.scripture_instructions), ice))

    body_sections = []
    n = 0
    for sec in g.sections:
        qs = []
        for q in sec.questions:
            n += 1
            qs.append("<div class='q'><span class='q-n'>%d</span>"
                      "<p class='ask'>%s</p></div>" % (n, _e(q)))
        body_sections.append(
            "<section class='seg rise'><div class='seg-head'><h2>%s</h2></div>"
            "<p class='setup'>%s</p>%s</section>"
            % (_e(sec.title), _e(sec.setup), "".join(qs)))

    closing = ("<section class='seg seg-commit rise'><div class='seg-head'>"
               "<h2>Closing and application</h2></div><p>%s</p>"
               "<p class='carry'>%s</p></section>"
               % (_e(g.closing_go_around), _e(g.prayer)))

    rows = "".join("<tr><td>%s</td><td>%s</td></tr>" % (_e(c.dynamic), _e(c.response))
                   for c in g.cheat_sheet)
    cheat = ("<section class='seg rise'><div class='seg-head'>"
             "<h2>Facilitator cheat sheet</h2></div>"
             "<div class='table-wrap'><table class='cheat'><thead><tr>"
             "<th>If this happens</th><th>Try this</th></tr></thead>"
             "<tbody>%s</tbody></table></div></section>" % rows)

    themes = ("<section class='seg rise'><div class='seg-head'>"
              "<h2>Key themes to reinforce</h2></div>"
              "<p class='instruction'>For you, not to read aloud</p>"
              "<ul class='themes'>%s</ul></section>"
              % "".join("<li>%s</li>" % _e(t) for t in g.key_themes))

    body = ("<div class='shell'>"
            "<a class='backlink' href='../index.html'>&larr; All guides</a>"
            "<article class='guide'>%s%s%s%s%s%s%s%s"
            "<p class='colophon'>Generated from the sermon (%s). Sermon content "
            "belongs to Traders Point Christian Church, this is a study aid, "
            "not a transcript.</p></article></div>"
            % (_header(g, None, (guide_filename(g, "html", "reflection"),
                                 "Reflection sheet")),
               glance, notes, opening, "".join(body_sections), closing, cheat, themes,
               _e(g.source)))
    return _doc(g.title, "../", body)


def render_reflection_page(g):
    """The participant sheet. No leader notes, no pastoral flags, no cheat sheet."""
    parts = []
    n = 0
    for sec in g.sections:
        qs = []
        for q in sec.reflection_questions:
            n += 1
            qs.append("<div class='q'><span class='q-n'>%d</span>"
                      "<p class='ask'>%s</p><div class='write'></div></div>"
                      % (n, _e(q)))
        parts.append("<section class='seg rise'><div class='seg-head'><h2>%s</h2>"
                     "</div>%s</section>" % (_e(sec.title), "".join(qs)))

    commit = ("<section class='seg seg-commit rise'><div class='seg-head'>"
              "<h2>This week</h2></div><p>%s</p><div class='write write-tall'></div>"
              "</section>" % _e(g.commitment_prompt))

    body = ("<div class='shell'>"
            "<a class='backlink' href='%s'>&larr; Leader guide</a>"
            "<article class='guide sheet'>%s%s%s</article></div>"
            % (guide_filename(g, "html", "guide"),
               _header(g, "Reflection sheet"), "".join(parts), commit))
    return _doc("%s — Reflection sheet" % g.title, "../", body)


def render_site(guides, latest_markdown=None):
    ordered = sorted(guides, key=lambda g: g.date or "", reverse=True)
    masthead = ("<header class='masthead'>"
                "<p class='eyebrow rise'>Traders Point Christian Church</p>"
                "<h1 class='rise'>Group <em>Guides</em></h1>"
                "<p class='blurb rise'>Discussion guides for the men's group, "
                "published each week after the Sunday message.</p></header>")

    featured, rest = "", ordered
    if ordered:
        g, rest = ordered[0], ordered[1:]
        featured = ("<a class='featured rise' href='guides/%s'>"
                    "<p class='eyebrow'>This week</p><h2>%s</h2>%s"
                    "<div class='cue'>Open the guide <span>&rarr;</span></div></a>"
                    % (_e(guide_filename(g, "html")), _e(g.title),
                       _meta_line(g.date, g.passage, getattr(g, "speaker", None))))

    rows, current = [], object()
    for g in rest:
        if g.series != current:
            current = g.series
            rows.append("<div class='series-head'><p class='eyebrow'>%s</p></div>"
                        % _e(current or "Other"))
        rows.append("<a class='entry' href='guides/%s'><span class='when'>%s</span>"
                    "<span class='what'>%s%s</span></a>"
                    % (_e(guide_filename(g, "html")), _e(_short_date(g.date)), _e(g.title),
                       "<span class='ref'>%s</span>" % _e(g.passage) if g.passage else ""))
    archive = "<section class='archive'>%s</section>" % "".join(rows) if rows else ""
    foot = ("<footer class='site-foot'><span>Generated weekly &middot; "
            "<a href='https://tpcc.org/messages'>tpcc.org</a></span>"
            "<span>%d guides</span></footer>" % len(ordered))
    return _doc("Group Guides · Traders Point", "",
                "<div class='shell'>%s%s%s%s</div>" % (masthead, featured, archive, foot))
