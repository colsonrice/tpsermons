"""Rendering: Guide -> HTML pages, markdown, and the participant sheet.

Classic mirrors the group's reference guide heading for heading. New is laid
out for leading live from a phone. Both share a participant reflection sheet
that assumes phones, not pens, and never carries pastoral flags.
"""
from __future__ import annotations

import html
import re

from .models import DEFAULT_MODE, CheatRow, Guide, Icebreaker, Question, Section

CHURCH = "Traders Point Christian Church"
TIME = "About 60 minutes"
GROUP = "About 10 to 12 men"
MATERIALS = "A Bible (your phone works) and this guide"
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
_REMEMBER = (
    "<script>document.addEventListener('click',function(e){"
    "var a=e.target.closest('[data-mode]');if(!a)return;"
    "try{localStorage.setItem('guideMode',a.getAttribute('data-mode'))}catch(_){}});"
    "</script>"
)
_PREFER = (
    "<script>(function(){var m;try{m=localStorage.getItem('guideMode')}catch(_){}"
    "if(!m)return;document.querySelectorAll('[data-'+m+']').forEach(function(a){"
    "a.setAttribute('href',a.getAttribute('data-'+m))})})();</script>"
)


def _e(text):
    return html.escape(str(text or ""))


def _doc(title, depth, body):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta name='color-scheme' content='light dark'>"
            "<title>%s</title>%s%s<link rel='stylesheet' href='%sassets/style.css'>"
            "</head><body>%s</body></html>" % (_e(title), _FONTS, _ICON, depth, body))


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


def guide_filename(guide, ext="md", kind="guide", mode=None):
    """Classic keeps the original names; New adds a -new suffix."""
    stem = "%s-%s" % (guide.date, slugify(guide.title))
    if (mode or getattr(guide, "mode", "classic")) == "new":
        stem += "-new"
    if kind == "reflection":
        stem += "-reflection"
    return "%s.%s" % (stem, ext)


def preacher_line(g):
    if not g.speaker:
        return ""
    return "%s, %s" % (g.speaker, g.speaker_role) if g.speaker_role else g.speaker


def _theme(text):
    """'Label: explanation' renders the label in bold."""
    label, sep, rest = text.partition(": ")
    if sep and len(label.split()) <= 8:
        return "<strong>%s:</strong> %s" % (_e(label), _e(rest))
    return _e(text)


# --- serialisation ----------------------------------------------------------

def guide_to_dict(g):
    return {
        "title": g.title, "series": g.series, "speaker": g.speaker,
        "speaker_role": g.speaker_role, "date": g.date, "passage": g.passage,
        "links": g.links, "source": g.source, "mode": g.mode,
        "guide_title": g.guide_title, "goal": g.goal,
        "scripture_instructions": g.scripture_instructions,
        "icebreakers": [{"label": i.label, "fits": i.fits, "question": i.question,
                         "note": i.note} for i in g.icebreakers],
        "sections": [{"title": s.title, "setup": s.setup, "minutes": s.minutes,
                      "say": s.say,
                      "questions": [{"ask": q.ask, "lead": q.lead, "probe": q.probe,
                                     "star": q.star} for q in s.questions],
                      "reflection_questions": list(s.reflection_questions)}
                     for s in g.sections],
        "closing_go_around": g.closing_go_around, "prayer": g.prayer,
        "cheat_sheet": [{"dynamic": c.dynamic, "response": c.response}
                        for c in g.cheat_sheet],
        "key_themes": list(g.key_themes), "commitment_prompt": g.commitment_prompt,
        "leader_notes": list(g.leader_notes), "thesis": g.thesis,
        "outline": list(g.outline), "sensitivities": list(g.sensitivities),
        "read_refs": list(g.read_refs), "obstacle": g.obstacle, "carry": g.carry,
    }


def guide_from_dict(d):
    return Guide(
        title=d["title"], series=d.get("series"), speaker=d.get("speaker"),
        speaker_role=d.get("speaker_role"), date=d["date"], passage=d.get("passage"),
        links=d.get("links", {}), source=d.get("source", ""),
        mode=d.get("mode", "classic"),
        guide_title=d.get("guide_title") or d["title"], goal=d["goal"],
        scripture_instructions=d["scripture_instructions"],
        icebreakers=[Icebreaker(i["label"], i.get("fits", ""), i["question"],
                                i.get("note", "")) for i in d["icebreakers"]],
        sections=[Section(
            title=s["title"], setup=s["setup"],
            questions=[Question(q["ask"], q.get("lead", ""), q.get("probe", ""),
                                bool(q.get("star", False)))
                       if isinstance(q, dict) else Question(q) for q in s["questions"]],
            reflection_questions=s["reflection_questions"],
            minutes=s.get("minutes", ""), say=s.get("say", ""))
            for s in d["sections"]],
        closing_go_around=d["closing_go_around"], prayer=d["prayer"],
        cheat_sheet=[CheatRow(c["dynamic"], c["response"]) for c in d["cheat_sheet"]],
        key_themes=d["key_themes"], commitment_prompt=d["commitment_prompt"],
        leader_notes=d.get("leader_notes", []), thesis=d.get("thesis", ""),
        outline=d.get("outline", []), sensitivities=d.get("sensitivities", []),
        read_refs=d.get("read_refs", []), obstacle=d.get("obstacle", ""),
        carry=d.get("carry", ""))


# --- markdown ---------------------------------------------------------------

def _front_matter(g, kind):
    L = ["---", "title: %s" % g.guide_title, "sermon: %s" % g.title,
         "date: %s" % g.date, "edition: %s" % g.mode, "kind: %s" % kind]
    for label, value in (("series", g.series), ("passage", g.passage),
                         ("preacher", preacher_line(g))):
        if value:
            L.append("%s: %s" % (label, value))
    return L + ["source: %s" % g.source, "---", ""]


def _md_links(g):
    return " · ".join("[%s](%s)" % (lbl, g.links[k]) for k, lbl in LINK_LABELS
                      if g.links.get(k))


def render_markdown(g):
    return _md_new(g) if g.mode == "new" else _md_classic(g)


def _md_classic(g):
    L = _front_matter(g, "guide") + ["# %s" % g.guide_title, ""]
    head = []
    if g.series:
        head.append("**Series:** %s" % g.series)
    head.append("**Message:** %s%s" % (g.title, " (%s)" % g.passage if g.passage else ""))
    if g.speaker:
        head.append("**Preacher:** %s" % preacher_line(g))
    head.append("**Church:** %s" % CHURCH)
    if _md_links(g):
        head.append("**Sermon link:** %s" % _md_links(g))
    L += ["  \n".join(head), "", "---", "", "## At a Glance", "",
          "**Time:** %s  \n**Group:** %s  \n**Materials:** %s  \n**Goal:** %s"
          % (TIME, GROUP, MATERIALS, g.goal), "", "---", "", "## Before You Begin", "",
          "*Leader notes. Read these ahead of time. They are for you, not to be read "
          "aloud.*", ""]
    for p in g.leader_notes:
        L += [p, ""]
    L += ["---", "", "## Opening (10 minutes)", "", g.scripture_instructions, "",
          "Then pick one icebreaker based on your group.", ""]
    for i in g.icebreakers:
        L += ["**Option %s (%s):** %s%s" % (i.label, i.fits, i.question,
                                            " %s" % i.note if i.note else ""), ""]
    for n, sec in enumerate(g.sections, 1):
        mins = " (%s minutes)" % sec.minutes if sec.minutes else ""
        L += ["---", "", "## Section %d: %s%s" % (n, sec.title, mins), "", sec.setup, ""]
        for q in sec.questions:
            L += [("%s **%s**" % (q.lead, q.ask)).strip(), ""]
    L += ["---", "", "## Closing and Application (5 minutes)", "", g.closing_go_around,
          "", "**Prayer:** %s" % g.prayer, "", "---", "", "## Facilitator Cheat Sheet", "",
          "| Dynamic | What to do |", "| --- | --- |"]
    L += ["| %s | %s |" % (c.dynamic, c.response) for c in g.cheat_sheet]
    L += ["", "---", "", "## Key Themes to Reinforce", "",
          "*These are for you to steer by if the discussion drifts. Do not read them "
          "aloud.*", ""]
    L += ["- %s" % t for t in g.key_themes] + [""]
    return "\n".join(L)


def _md_new(g):
    L = _front_matter(g, "guide") + ["# %s" % g.guide_title, ""]
    L += [" · ".join(b for b in (g.title, g.passage, preacher_line(g)) if b), ""]
    if _md_links(g):
        L += [_md_links(g), ""]
    L += ["## Tonight", ""]
    L += ["1. Read and icebreaker"] + ["%d. %s" % (n + 2, s.title)
                                       for n, s in enumerate(g.sections)]
    k = len(g.sections) + 2
    L += ["%d. Get honest" % k, "%d. Go around and pray" % (k + 1), "",
          "## Know Before You Walk In", "", g.goal, "", "> %s" % g.thesis, ""]
    L += ["%d. %s" % (n, o) for n, o in enumerate(g.outline, 1)] + [""]
    if g.sensitivities:
        L += ["**Handle with care:**", ""] + ["- %s" % s for s in g.sensitivities] + [""]
    L += ["## Open", "", "**Read:** %s" % " · ".join(g.read_refs), "",
          g.scripture_instructions, ""]
    for i in g.icebreakers:
        L += ["**%s (%s):** %s%s" % (i.label, i.fits, i.question,
                                     " *%s*" % i.note if i.note else ""), ""]
    for sec in g.sections:
        L += ["## %s" % sec.title, "", "**Say:** %s" % sec.say, ""]
        for q in sec.questions:
            star = " *(must ask)*" if q.star else ""
            L += [("%s **%s**%s" % (q.lead, q.ask, star)).strip(),
                  "", "*Follow up:* %s" % q.probe, ""]
    L += ["## Get Honest", "", "**%s**" % g.obstacle, "",
          "## Go Around and Pray", "", g.closing_go_around, "",
          "**Pray:** %s" % g.prayer, "", "**Next week we ask:** %s" % g.carry, "",
          "## If the Room...", ""]
    L += ["- **%s:** %s" % (c.dynamic, c.response) for c in g.cheat_sheet]
    L += ["", "## Steer By", ""] + ["- %s" % t for t in g.key_themes] + [""]
    return "\n".join(L)


PHONE_HINT = ("Put it in a note on your phone, then text it to the man who will ask "
              "you about it next week.")


def render_reflection_markdown(g):
    L = _front_matter(g, "reflection") + ["# %s" % g.guide_title, "",
                                          "*Reflection sheet*", ""]
    meta = " · ".join(b for b in (g.series, g.passage, preacher_line(g)) if b)
    if meta:
        L += [meta, "", "---", ""]
    n = 0
    for sec in g.sections:
        L += ["## %s" % sec.title, ""]
        for r in sec.reflection_questions:
            n += 1
            L += ["%d. **%s**" % (n, r)]
        L += [""]
    L += ["---", "", "## This Week", "", g.commitment_prompt, "", PHONE_HINT, ""]
    if g.carry:
        L += ["*Next week the group asks: %s*" % g.carry, ""]
    return "\n".join(L)


# --- HTML pieces ------------------------------------------------------------

def _toggle(g, alt_href):
    if not alt_href:
        return ""
    def tab(m, label):
        here = m == g.mode
        return ("<a class='%s' href='%s' data-mode='%s'%s>%s</a>"
                % ("on" if here else "", "#" if here else _e(alt_href), m,
                   " aria-current='page'" if here else "", label))
    return ("<nav class='mode-toggle' aria-label='Guide edition'>%s%s</nav>"
            % (tab("new", "New"), tab("classic", "Classic")))


def _link_pills(g, sheet=True):
    pills = "".join("<a href=\"%s\">%s</a>" % (_e(g.links[k]), _e(lbl))
                    for k, lbl in LINK_LABELS if g.links.get(k))
    if sheet:
        pills += ("<a class='alt' href=\"%s\">Reflection sheet</a>"
                  % _e(guide_filename(g, "html", "reflection")))
    return "<div class='links'>%s</div>" % pills


def _shell(inner, back_href="../index.html", back_label="All guides"):
    return ("<div class='shell'><a class='backlink' href='%s'>&larr; %s</a>%s</div>"
            % (back_href, back_label, inner))


def _colophon(g):
    return ("<p class='colophon'>Generated from the sermon (%s). Sermon content "
            "belongs to %s. This is a study aid, not a transcript.</p>"
            % (_e(g.source), CHURCH))


def render_guide_page(g, alt_href=None):
    body = _classic_page(g, alt_href) if g.mode != "new" else _new_page(g, alt_href)
    return _doc("%s · %s" % (g.guide_title, g.title), "../", body + _REMEMBER)


def _classic_page(g, alt_href):
    rows = []
    if g.series:
        rows.append(("Series", _e(g.series)))
    rows.append(("Message", "%s%s" % (_e(g.title),
                                      " <span class='passage'>(%s)</span>" % _e(g.passage)
                                      if g.passage else "")))
    if g.speaker:
        rows.append(("Preacher", _e(preacher_line(g))))
    rows.append(("Church", CHURCH))
    header_block = "<dl class='kv'>%s</dl>" % "".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % r for r in rows)

    head = ("<header class='guide-head rise'>%s<h1>%s</h1>%s%s</header>"
            % (_toggle(g, alt_href), _e(g.guide_title), header_block, _link_pills(g)))

    glance = ("<section class='block rise'><h2>At a Glance</h2><dl class='kv'>"
              "<div><dt>Time</dt><dd>%s</dd></div><div><dt>Group</dt><dd>%s</dd></div>"
              "<div><dt>Materials</dt><dd>%s</dd></div><div><dt>Goal</dt><dd>%s</dd></div>"
              "</dl></section>" % (TIME, GROUP, MATERIALS, _e(g.goal)))

    notes = ("<section class='block notes rise'><h2>Before You Begin</h2>"
             "<p class='intro'>Leader notes. Read these ahead of time. They are for you, "
             "not to be read aloud.</p>%s</section>"
             % "".join("<p>%s</p>" % _e(p) for p in g.leader_notes))

    options = "".join(
        "<div class='option'><p class='option-label'>Option %s <span>(%s)</span></p>"
        "<p class='ask'>%s</p>%s</div>"
        % (_e(i.label), _e(i.fits), _e(i.question),
           "<p class='note'>%s</p>" % _e(i.note) if i.note else "") for i in g.icebreakers)
    opening = ("<section class='block rise'><h2>Opening <span class='mins'>(10 minutes)"
               "</span></h2><p>%s</p><p class='intro'>Then pick one icebreaker based on "
               "your group.</p>%s</section>" % (_e(g.scripture_instructions), options))

    sections = []
    for n, sec in enumerate(g.sections, 1):
        qs = "".join("<div class='cq'>%s<p class='ask'>%s</p></div>"
                     % ("<p class='lead'>%s</p>" % _e(q.lead) if q.lead else "", _e(q.ask))
                     for q in sec.questions)
        mins = " <span class='mins'>(%s minutes)</span>" % _e(sec.minutes) if sec.minutes else ""
        sections.append("<section class='block rise'><h2>Section %d: %s%s</h2>"
                        "<p class='setup'>%s</p>%s</section>"
                        % (n, _e(sec.title), mins, _e(sec.setup), qs))

    closing = ("<section class='block rise'><h2>Closing and Application "
               "<span class='mins'>(5 minutes)</span></h2><p>%s</p>"
               "<p><strong>Prayer:</strong> %s</p></section>"
               % (_e(g.closing_go_around), _e(g.prayer)))

    cheat = ("<section class='block rise'><h2>Facilitator Cheat Sheet</h2>"
             "<div class='table-wrap'><table class='cheat'><thead><tr><th>Dynamic</th>"
             "<th>What to do</th></tr></thead><tbody>%s</tbody></table></div></section>"
             % "".join("<tr><td>%s</td><td>%s</td></tr>" % (_e(c.dynamic), _e(c.response))
                       for c in g.cheat_sheet))

    themes = ("<section class='block rise'><h2>Key Themes to Reinforce</h2>"
              "<p class='intro'>These are for you to steer by if the discussion drifts. "
              "Do not read them aloud.</p><ul class='themes'>%s</ul></section>"
              % "".join("<li>%s</li>" % _theme(t) for t in g.key_themes))

    return _shell("<article class='guide classic'>%s%s%s%s%s%s%s%s%s</article>"
                  % (head, glance, notes, opening, "".join(sections), closing, cheat,
                     themes, _colophon(g)))


def _new_page(g, alt_href):
    sub = " · ".join(_e(b) for b in (g.title, g.passage, preacher_line(g)) if b)
    head = ("<header class='guide-head rise'>%s%s<h1>%s</h1><p class='sub'>%s</p>%s"
            "</header>" % (_toggle(g, alt_href),
                           "<p class='eyebrow'>%s</p>" % _e(g.series) if g.series else "",
                           _e(g.guide_title), sub, _link_pills(g)))

    steps = [("open", "Read and icebreaker")]
    steps += [("s%d" % n, sec.title) for n, sec in enumerate(g.sections, 1)]
    steps += [("honest", "Get honest"), ("close", "Go around and pray")]
    runshow = ("<nav class='runshow rise' aria-label='Tonight'><p class='eyebrow'>Tonight"
               "</p><ol>%s</ol></nav>" % "".join(
                   "<li><a href='#%s'><span class='n'>%d</span>%s</a></li>"
                   % (anchor, i, _e(label)) for i, (anchor, label) in enumerate(steps, 1)))

    care = ""
    if g.sensitivities:
        care = ("<div class='care'><p class='mini'>Handle with care</p><ul>%s</ul></div>"
                % "".join("<li>%s</li>" % _e(s) for s in g.sensitivities))
    brief = ("<section class='brief rise' id='brief'><p class='eyebrow'>Know before you "
             "walk in</p><p class='goal'>%s</p><blockquote class='thesis'><span "
             "class='mini'>The one sentence</span>%s</blockquote><p class='mini'>The "
             "sermon's moves</p><ol class='outline'>%s</ol>%s</section>"
             % (_e(g.goal), _e(g.thesis),
                "".join("<li>%s</li>" % _e(o) for o in g.outline), care))

    def step_head(n, title):
        return "<h2><span class='step-n'>%s</span>%s</h2>" % (n, _e(title))

    refs = "".join("<span class='ref-chip'>%s</span>" % _e(r) for r in g.read_refs)
    ice = "".join(
        "<div class='ice-card'><p class='badge'>%s <span>%s</span></p><p class='ask'>%s"
        "</p>%s</div>" % (_e(i.label), _e(i.fits), _e(i.question),
                          "<p class='note'>%s</p>" % _e(i.note) if i.note else "")
        for i in g.icebreakers)
    open_s = ("<section class='step rise' id='open'>%s<div class='refs'>%s</div>"
              "<p class='instr'>%s</p><p class='mini'>Pick one icebreaker</p>"
              "<div class='ice-grid'>%s</div></section>"
              % (step_head(1, "Open"), refs, _e(g.scripture_instructions), ice))

    body = []
    for n, sec in enumerate(g.sections, 1):
        qs = "".join(
            "<li class='q%s'>%s%s<p class='ask'>%s</p><p class='probe'><span>Follow up"
            "</span>%s</p></li>"
            % (" star" if q.star else "",
               "<span class='must'>Must ask</span>" if q.star else "",
               "<p class='lead'>%s</p>" % _e(q.lead) if q.lead else "",
               _e(q.ask), _e(q.probe)) for q in sec.questions)
        body.append("<section class='step rise' id='s%d'>%s<p class='say'><span>Say"
                    "</span>%s</p><details class='context'><summary>Background"
                    "</summary><p>%s</p></details><ol class='qs'>%s</ol></section>"
                    % (n, step_head(n + 1, sec.title), _e(sec.say), _e(sec.setup), qs))

    k = len(g.sections) + 2
    honest = ("<section class='step honest rise' id='honest'>%s<p class='ask big'>%s</p>"
              "</section>" % (step_head(k, "Get honest"), _e(g.obstacle)))
    close = ("<section class='step close rise' id='close'>%s<p class='script'>%s</p>"
             "<p><strong>Pray:</strong> %s</p><p class='carry'><strong>Next week we ask:"
             "</strong> %s</p></section>"
             % (step_head(k + 1, "Go around and pray"), _e(g.closing_go_around),
                _e(g.prayer), _e(g.carry)))

    room = ("<section class='room rise'><h2>If the room...</h2><div class='cards'>%s</div>"
            "</section>" % "".join("<div class='card'><p class='dyn'>%s</p><p>%s</p></div>"
                                   % (_e(c.dynamic), _e(c.response)) for c in g.cheat_sheet))
    themes = ("<details class='steer rise'><summary>Steer by these themes</summary>"
              "<ul class='themes'>%s</ul></details>"
              % "".join("<li>%s</li>" % _theme(t) for t in g.key_themes))

    return _shell("<article class='guide new'>%s%s%s%s%s%s%s%s%s%s</article>"
                  % (head, runshow, brief, open_s, "".join(body), honest, close, room,
                     themes, _colophon(g)))


def render_reflection_page(g):
    meta = " · ".join(_e(b) for b in (g.series, g.passage, preacher_line(g)) if b)
    parts, n = [], 0
    for sec in g.sections:
        items = []
        for r in sec.reflection_questions:
            n += 1
            items.append("<li value='%d'>%s</li>" % (n, _e(r)))
        parts.append("<section class='block rise'><h2>%s</h2><ol class='rq'>%s</ol>"
                     "</section>" % (_e(sec.title), "".join(items)))
    carry = ("<p class='carry'>Next week the group asks: %s</p>" % _e(g.carry)
             if g.carry else "")
    commit = ("<section class='block commit rise'><h2>This Week</h2><p class='ask'>%s</p>"
              "<p class='hint'>%s</p>%s</section>" % (_e(g.commitment_prompt), PHONE_HINT,
                                                      carry))
    head = ("<header class='guide-head rise'>%s<h1>%s</h1><p class='sub'>Reflection "
            "sheet</p><p class='meta-line'>%s</p></header>"
            % ("<p class='eyebrow'>%s</p>" % _e(g.series) if g.series else "",
               _e(g.guide_title), meta))
    body = _shell("<article class='guide sheet'>%s%s%s</article>"
                  % (head, "".join(parts), commit),
                  back_href=guide_filename(g, "html", "guide"), back_label="Leader guide")
    return _doc("%s · Reflection sheet" % g.guide_title, "../", body)


# --- index ------------------------------------------------------------------

def _weeks(guides):
    weeks = {}
    for g in guides:
        weeks.setdefault((g.date, slugify(g.title)), {})[g.mode] = g
    return weeks


def _edition_link(editions):
    first = editions.get(DEFAULT_MODE) or next(iter(editions.values()))
    attrs = "".join(" data-%s='guides/%s'" % (m, _e(guide_filename(g, "html")))
                    for m, g in editions.items())
    return "guides/%s" % _e(guide_filename(first, "html")), attrs, first


def render_site(guides, latest_markdown=None):
    weeks = sorted(_weeks(guides).items(), key=lambda kv: kv[0][0], reverse=True)
    masthead = ("<header class='masthead'>"
                "<p class='eyebrow rise'>Traders Point Christian Church</p>"
                "<h1 class='rise'>Group <em>Guides</em></h1>"
                "<p class='blurb rise'>Discussion guides for the men's group, published "
                "each week after the Sunday message.</p></header>")
    featured, rest = "", weeks
    if weeks:
        (_k, editions), rest = weeks[0], weeks[1:]
        href, attrs, g = _edition_link(editions)
        featured = ("<a class='featured rise' href='%s'%s><p class='eyebrow'>This week"
                    "</p><h2>%s</h2><p class='sermon'>%s</p><div class='meta'>%s</div>"
                    "<div class='cue'>Open the guide <span>&rarr;</span></div></a>"
                    % (href, attrs, _e(g.guide_title), _e(g.title), " · ".join(
                        "<span>%s</span>" % _e(b) for b in
                        (_pretty_date(g.date), g.passage, preacher_line(g)) if b)))
    rows, current = [], object()
    for _k, editions in rest:
        href, attrs, g = _edition_link(editions)
        if g.series != current:
            current = g.series
            rows.append("<div class='series-head'><p class='eyebrow'>%s</p></div>"
                        % _e(current or "Other"))
        rows.append("<a class='entry' href='%s'%s><span class='when'>%s</span><span "
                    "class='what'>%s<span class='ref'>%s</span></span></a>"
                    % (href, attrs, _e(_short_date(g.date)), _e(g.guide_title),
                       " · ".join(_e(b) for b in (g.title, g.passage) if b)))
    archive = "<section class='archive'>%s</section>" % "".join(rows) if rows else ""
    foot = ("<footer class='site-foot'><span>Generated weekly &middot; <a "
            "href='https://tpcc.org/messages'>tpcc.org</a></span><span>%d guides</span>"
            "</footer>" % len(weeks))
    return _doc("Group Guides · Traders Point", "",
                "<div class='shell'>%s%s%s%s</div>%s"
                % (masthead, featured, archive, foot, _PREFER))
