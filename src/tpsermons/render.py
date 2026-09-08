"""Rendering: Guide -> markdown, and guides -> a browsable site.

Publishes derived guides only. Sermon transcripts and audio are never written
here; each guide links back to TPCC's own message page and video instead.
"""
from __future__ import annotations

import html
import re
from typing import List, Optional

from .models import Guide

LINK_LABELS = [("tpcc", "Message page"), ("youtube", "Watch"), ("podcast", "Listen")]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "message"


def guide_filename(guide: Guide) -> str:
    return "%s-%s.md" % (guide.date, slugify(guide.title))


def render_markdown(guide: Guide) -> str:
    lines = [
        "---",
        "title: %s" % guide.title,
        "date: %s" % guide.date,
    ]
    if guide.series:
        lines.append("series: %s" % guide.series)
    if guide.passage:
        lines.append("passage: %s" % guide.passage)
    if guide.speaker:
        lines.append("speaker: %s" % guide.speaker)
    lines += ["source: %s" % guide.source, "---", ""]

    lines.append("# %s" % guide.title)
    meta = [b for b in (guide.series, guide.passage, guide.speaker) if b]
    if meta:
        lines += ["", " · ".join(meta)]

    links = ["[%s](%s)" % (label, guide.links[key])
             for key, label in LINK_LABELS if guide.links.get(key)]
    if links:
        lines += ["", " · ".join(links)]

    lines += ["", "## Recap", "", guide.recap, "", "## Discuss"]
    for block in guide.discuss:
        lines += ["", "### %s" % block.heading, ""]
        lines += ["%d. %s" % (i, q) for i, q in enumerate(block.questions, 1)]

    lines += ["", "## Take Action", "", guide.take_action, "", "## Reflections", ""]
    lines += ["- %s" % r for r in guide.reflections]

    lines += ["", "---", "",
              "*Guide generated from the sermon; text source: %s. "
              "Sermon content belongs to Traders Point Christian Church.*" % guide.source, ""]
    return "\n".join(lines)


SECTION_CLASS = {
    "recap": "sec-recap",
    "discuss": "sec-discuss",
    "take action": "sec-action",
    "reflections": "sec-reflections",
}

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
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


def _doc(title: str, depth: str, body: str) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>%s</title>%s%s"
        "<link rel='stylesheet' href='%sassets/style.css'>"
        "</head><body>%s</body></html>" % (html.escape(title), _FONTS, _ICON, depth, body)
    )


def _inline(text: str) -> str:
    out = html.escape(text)
    out = _LINK.sub(lambda m: "<a href=\"%s\">%s</a>" % (m.group(2), m.group(1)), out)
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)


def parse_front_matter(md: str):
    """Return (fields, body) from a guide markdown document."""
    if not md.startswith("---"):
        return {}, md
    end = md.find("\n---", 3)
    if end == -1:
        return {}, md
    block = md[3:end]
    fields = dict(re.findall(r"^(\w+): (.*)$", block, re.M))
    return fields, md[end + 4:].lstrip("\n")


def strip_front_matter(md: str) -> str:
    return parse_front_matter(md)[1]


def _blocks_to_html(lines) -> str:
    """Render the markdown subset render_markdown emits."""
    out, list_tag = [], None

    def close():
        nonlocal list_tag
        if list_tag:
            out.append("</%s>" % list_tag)
            list_tag = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            close()
            continue
        if line.startswith("### "):
            close(); out.append("<h3>%s</h3>" % _inline(line[4:]))
        elif line.startswith("## "):
            close(); out.append("<h2>%s</h2>" % _inline(line[3:]))
        elif line.startswith("# "):
            close(); out.append("<h1>%s</h1>" % _inline(line[2:]))
        elif line.startswith("---"):
            close(); out.append("<hr>")
        elif re.match(r"^\d+\. ", line):
            if list_tag != "ol":
                close(); out.append("<ol>"); list_tag = "ol"
            out.append("<li>%s</li>" % _inline(re.sub(r"^\d+\. ", "", line)))
        elif line.startswith("- "):
            if list_tag != "ul":
                close(); out.append("<ul>"); list_tag = "ul"
            out.append("<li>%s</li>" % _inline(line[2:]))
        else:
            close(); out.append("<p>%s</p>" % _inline(line))
    close()
    return "\n".join(out)


def markdown_to_html(md: str) -> str:
    return _blocks_to_html(strip_front_matter(md).split("\n"))


def _meta_line(fields) -> str:
    bits = []
    if fields.get("date"):
        bits.append("<span>%s</span>" % html.escape(_pretty_date(fields["date"])))
    if fields.get("speaker"):
        bits.append("<span>%s</span>" % html.escape(fields["speaker"]))
    if fields.get("passage"):
        bits.append("<span class='passage'>%s</span>" % html.escape(fields["passage"]))
    return "<div class='meta'>%s</div>" % "".join(bits)


def _pretty_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except ValueError:
        return iso
    months = ("January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December")
    return "%s %d, %d" % (months[m - 1], d, y)


def _short_date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except ValueError:
        return iso
    return "%s %d" % (("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                       "Aug", "Sep", "Oct", "Nov", "Dec")[m - 1], d)


def render_guide_page(md: str) -> str:
    """A standalone, readable page for one guide."""
    fields, body = parse_front_matter(md)
    title = fields.get("title", "Group Guide")

    links_html = ""
    for line in body.split("\n"):
        if line.startswith("[") and "](" in line:
            links_html = "<div class='links'>%s</div>" % "".join(
                "<a href=\"%s\">%s</a>" % (u, html.escape(l)) for l, u in _LINK.findall(line))
            break

    sections, current, buf = [], None, []
    for line in body.split("\n"):
        if line.startswith("## "):
            if current:
                sections.append((current, buf))
            current, buf = line[3:].strip(), []
        elif current is not None:
            if line.startswith("---") or (line.startswith("*") and line.endswith("*")):
                continue
            buf.append(line)
    if current:
        sections.append((current, buf))

    parts = []
    for heading, lines in sections:
        cls = SECTION_CLASS.get(heading.lower(), "sec")
        parts.append("<section class='%s rise'><h2>%s</h2>%s</section>"
                     % (cls, html.escape(heading), _blocks_to_html(lines)))

    src = fields.get("source", "")
    colophon = (
        "<p class='colophon'>Generated from the sermon audio%s. "
        "Sermon content belongs to Traders Point Christian Church &mdash; "
        "these guides are a study aid, not a transcript.</p>"
        % (" (%s)" % html.escape(src) if src else "")
    )

    body_html = (
        "<div class='shell'>"
        "<a class='backlink' href='../index.html'>&larr; All guides</a>"
        "<article class='guide'>"
        "<header class='guide-head rise'>"
        "%s<h1>%s</h1>%s%s"
        "</header>%s%s</article></div>"
        % ("<p class='eyebrow'>%s</p>" % html.escape(fields["series"]) if fields.get("series") else "",
           html.escape(title), _meta_line(fields), links_html, "".join(parts), colophon)
    )
    return _doc(title, "../", body_html)


def render_site(guides, latest_markdown=None):
    """The index: this week's guide featured, everything else as an archive."""
    ordered = sorted(guides, key=lambda g: g.date or "", reverse=True)

    masthead = (
        "<header class='masthead'>"
        "<p class='eyebrow rise'>Traders Point Christian Church</p>"
        "<h1 class='rise'>Group <em>Guides</em></h1>"
        "<p class='blurb rise'>Discussion guides for small groups, published "
        "each week after the Sunday message.</p>"
        "</header>"
    )

    featured = ""
    rest = ordered
    if ordered:
        g = ordered[0]
        rest = ordered[1:]
        featured = (
            "<a class='featured rise' href='guides/%s'>"
            "<p class='eyebrow'>This week</p><h2>%s</h2>%s"
            "<div class='cue'>Open the guide <span>&rarr;</span></div></a>"
            % (html.escape(guide_filename(g).replace(".md", ".html")),
               html.escape(g.title),
               _meta_line({"date": g.date, "passage": g.passage,
                           "speaker": getattr(g, "speaker", None)}))
        )

    rows, current = [], object()
    for g in rest:
        if g.series != current:
            current = g.series
            rows.append("<div class='series-head'><p class='eyebrow'>%s</p></div>"
                        % html.escape(current or "Other"))
        rows.append(
            "<a class='entry' href='guides/%s'><span class='when'>%s</span>"
            "<span class='what'>%s%s</span></a>"
            % (html.escape(guide_filename(g).replace(".md", ".html")),
               html.escape(_short_date(g.date)), html.escape(g.title),
               "<span class='ref'>%s</span>" % html.escape(g.passage) if g.passage else "")
        )

    archive = "<section class='archive'>%s</section>" % "".join(rows) if rows else ""
    foot = ("<footer class='site-foot'><span>Generated weekly &middot; "
            "<a href='https://tpcc.org/messages'>tpcc.org</a></span>"
            "<span>%d guides</span></footer>" % len(ordered))

    return _doc("Group Guides \u00b7 Traders Point",
                "", "<div class='shell'>%s%s%s%s</div>"
                % (masthead, featured, archive, foot))
