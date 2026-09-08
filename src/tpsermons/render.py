"""Rendering: Guide -> markdown, and guides -> a browsable site.

Publishes derived guides only. Sermon transcripts and audio are never written
here; each guide links back to TPCC's own message page and video instead.
"""
from __future__ import annotations

import html
import re
from typing import List, Optional

from .models import SEGMENTS, DiscussBlock, Guide

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
LINK_LABELS = [("tpcc", "Message page"), ("youtube", "Watch"), ("podcast", "Listen")]


def _e(text):
    return html.escape(text or "")


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


# --- serialisation: JSON is the durable render source ----------------------

def guide_to_dict(g):
    return {
        "title": g.title, "series": g.series, "speaker": g.speaker, "date": g.date,
        "passage": g.passage, "links": g.links, "source": g.source,
        "leader_notes": list(g.leader_notes), "opener": g.opener, "context": g.context,
        "read_aloud": g.read_aloud, "observation": g.observation,
        "discuss": [{"heading": b.heading, "question": b.question,
                     "probes": list(b.probes)} for b in g.discuss],
        "obstacle": g.obstacle, "commit": g.commit, "carry": g.carry,
    }


def guide_from_dict(d):
    return Guide(
        title=d["title"], series=d.get("series"), speaker=d.get("speaker"),
        date=d["date"], passage=d.get("passage"), links=d.get("links", {}),
        leader_notes=d["leader_notes"], opener=d["opener"], context=d["context"],
        read_aloud=d["read_aloud"], observation=d["observation"],
        discuss=[DiscussBlock(b["heading"], b["question"], b["probes"])
                 for b in d["discuss"]],
        obstacle=d["obstacle"], commit=d["commit"], carry=d["carry"],
        source=d.get("source", ""))


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "message"


def guide_filename(guide, ext="md"):
    return "%s-%s.%s" % (guide.date, slugify(guide.title), ext)


# --- markdown (human-readable source of truth in git) -----------------------

def render_markdown(g):
    L = ["---", "title: %s" % g.title, "date: %s" % g.date]
    if g.series:
        L.append("series: %s" % g.series)
    if g.passage:
        L.append("passage: %s" % g.passage)
    if g.speaker:
        L.append("speaker: %s" % g.speaker)
    L += ["source: %s" % g.source, "---", "", "# %s" % g.title, ""]

    meta = [b for b in (g.series, g.passage, g.speaker) if b]
    if meta:
        L += [" · ".join(meta), ""]
    links = ["[%s](%s)" % (lbl, g.links[k]) for k, lbl in LINK_LABELS if g.links.get(k)]
    if links:
        L += [" · ".join(links), ""]

    L += ["## Leader Notes", ""] + ["- %s" % n for n in g.leader_notes] + [""]
    for label, mins, mode in SEGMENTS:
        L.append("## %s · %d min · %s" % (label, mins, mode))
        L.append("")
        if label == "Open":
            L += [g.opener, ""]
        elif label == "Read":
            L += [g.context, "", g.read_aloud, "", g.observation, ""]
        elif label == "Dig in":
            for b in g.discuss:
                L += ["### %s" % b.heading, "", b.question, ""]
                L += ["- %s" % p for p in b.probes] + [""]
        elif label == "Regroup":
            L += [g.obstacle, ""]
        else:
            L += [g.commit, "", "**Next week:** %s" % g.carry, ""]

    L += ["---", "",
          "*Generated from the sermon (%s). Sermon content belongs to Traders "
          "Point Christian Church; this is a study aid, not a transcript.*" % g.source, ""]
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


def _segment(label, mins, mode, inner, cls):
    return ("<section class='seg %s rise'>"
            "<div class='seg-head'><h2>%s</h2>"
            "<span class='chip chip-time'>%d min</span>"
            "<span class='chip chip-mode'>%s</span></div>%s</section>"
            % (cls, _e(label), mins, _e(mode), inner))


def render_guide_page(g):
    """A standalone, runnable page for one guide."""
    mins = dict((label, m) for label, m, _ in SEGMENTS)
    mode = dict((label, md) for label, _, md in SEGMENTS)

    notes = "<aside class='leader-notes rise'><p class='eyebrow'>Before you start</p><ul>%s</ul></aside>" % (
        "".join("<li>%s</li>" % _e(n) for n in g.leader_notes))

    open_html = "<p class='ask'>%s</p>" % _e(g.opener)

    read_html = ("<p class='context'>%s</p><p class='read-aloud'>%s</p>"
                 "<p class='ask'>%s</p>" % (_e(g.context), _e(g.read_aloud), _e(g.observation)))

    blocks = []
    for i, b in enumerate(g.discuss, 1):
        probes = "".join("<li>%s</li>" % _e(p) for p in b.probes)
        blocks.append(
            "<div class='block'><div class='block-head'>"
            "<span class='block-n'>%d</span><h3>%s</h3></div>"
            "<p class='ask'>%s</p>"
            "<details class='probes'><summary>If it stalls</summary><ul>%s</ul></details>"
            "</div>" % (i, _e(b.heading), _e(b.question), probes))
    dig_html = ("<p class='instruction'>Break into groups of four. "
                "Everyone answers.</p>%s" % "".join(blocks))

    regroup_html = ("<p class='instruction'>Back together. One man per group "
                    "shares where his conversation went.</p><p class='ask'>%s</p>"
                    % _e(g.obstacle))

    commit_html = ("<p>%s</p><p class='carry'><strong>Next week we ask:</strong> %s</p>"
                   % (_e(g.commit), _e(g.carry)))

    segs = (_segment("Open", mins["Open"], mode["Open"], open_html, "seg-open")
            + _segment("Read", mins["Read"], mode["Read"], read_html, "seg-read")
            + _segment("Dig in", mins["Dig in"], mode["Dig in"], dig_html, "seg-dig")
            + _segment("Regroup", mins["Regroup"], mode["Regroup"], regroup_html, "seg-regroup")
            + _segment("Commit", mins["Commit"], mode["Commit"], commit_html, "seg-commit"))

    links = "".join("<a href=\"%s\">%s</a>" % (g.links[k], _e(lbl))
                    for k, lbl in LINK_LABELS if g.links.get(k))
    total = sum(m for _, m, _ in SEGMENTS)

    body = ("<div class='shell'>"
            "<a class='backlink' href='../index.html'>&larr; All guides</a>"
            "<article class='guide'>"
            "<header class='guide-head rise'>%s<h1>%s</h1>%s"
            "<div class='links'>%s</div>"
            "<p class='runtime'>%d minutes &middot; groups of four for the middle</p>"
            "</header>%s%s"
            "<p class='colophon'>Generated from the sermon (%s). Sermon content "
            "belongs to Traders Point Christian Church &mdash; this is a study "
            "aid, not a transcript.</p></article></div>"
            % ("<p class='eyebrow'>%s</p>" % _e(g.series) if g.series else "",
               _e(g.title), _meta_line(g.date, g.passage, g.speaker), links,
               total, notes, segs, _e(g.source)))
    return _doc(g.title, "../", body)


def render_site(guides, latest_markdown=None):
    ordered = sorted(guides, key=lambda g: g.date or "", reverse=True)
    masthead = ("<header class='masthead'>"
                "<p class='eyebrow rise'>Traders Point Christian Church</p>"
                "<h1 class='rise'>Group <em>Guides</em></h1>"
                "<p class='blurb rise'>Discussion guides for men's small groups, "
                "published each week after the Sunday message. Built for about "
                "an hour of conversation.</p></header>")

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
    return _doc("Group Guides \u00b7 Traders Point", "",
                "<div class='shell'>%s%s%s%s</div>" % (masthead, featured, archive, foot))
