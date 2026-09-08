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


_STYLE = (
    "body{font:16px/1.6 system-ui,-apple-system,sans-serif;max-width:42rem;"
    "margin:2rem auto;padding:0 1rem;color:#222}"
    "h1{margin-bottom:.2rem;line-height:1.25}"
    "h2{margin-top:2rem;font-size:1rem;text-transform:uppercase;"
    "letter-spacing:.05em;color:#666}"
    "h3{margin-top:1.5rem;font-size:1.05rem}"
    "a{color:#0b5}small{color:#777}"
    "ol,ul{padding-left:1.2rem}li{margin:.35rem 0}"
    "hr{border:0;border-top:1px solid #eee;margin:2rem 0}"
    "em{color:#777;font-size:.9rem}")

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _inline(text: str) -> str:
    out = html.escape(text)
    out = _LINK.sub(lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), out)
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", out)


def strip_front_matter(md: str) -> str:
    if md.startswith("---"):
        end = md.find("\n---", 3)
        if end != -1:
            return md[end + 4:].lstrip("\n")
    return md


def markdown_to_html(md: str) -> str:
    """Convert the exact markdown subset render_markdown emits."""
    lines = strip_front_matter(md).split("\n")
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


def render_guide_page(md: str) -> str:
    """A standalone, readable HTML page for one guide."""
    body = markdown_to_html(md)
    m = re.search(r"<h1>(.*?)</h1>", body)
    title = re.sub(r"<[^>]+>", "", m.group(1)) if m else "Group Guide"
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>%s</title><style>%s</style>"
        "<p><a href='../index.html'>&larr; All guides</a></p>%s" % (title, _STYLE, body))


def render_site(guides: List[Guide], latest_markdown: Optional[str] = None) -> str:
    """A minimal static index: newest guide first, then an archive by series."""
    def esc(s):
        return html.escape(s or "")

    rows = []
    current = None
    for g in sorted(guides, key=lambda x: x.date, reverse=True):
        if g.series != current:
            current = g.series
            rows.append("<h2>%s</h2>" % esc(current or "Other"))
        rows.append(
            '<p><a href="guides/%s">%s</a> <small>%s%s</small></p>' % (
                esc(guide_filename(g).replace('.md', '.html')), esc(g.title), esc(g.date),
                " · " + esc(g.passage) if g.passage else ""))

    return (
        "<!doctype html><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>TPCC Group Guides</title>"
        "<style>body{font:16px/1.6 system-ui,sans-serif;max-width:42rem;"
        "margin:2rem auto;padding:0 1rem;color:#222}"
        "h1{margin-bottom:.2rem}h2{margin-top:2rem;font-size:1rem;"
        "text-transform:uppercase;letter-spacing:.05em;color:#666}"
        "a{color:#0b5}small{color:#777}</style>"
        "<h1>Group Discussion Guides</h1>"
        "<p>Weekly small-group guides generated from Traders Point Christian "
        "Church sermons.</p>" + "\n".join(rows))
