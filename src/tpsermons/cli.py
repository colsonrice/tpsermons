"""Entry point wiring discover -> source -> generate -> publish.

Real fetchers are injected via `Deps` so the whole pipeline is testable without
network, an API key, or ffmpeg.
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import json

from . import feed, mail, render, tpcc, transcribe, youtube
from .generate import generate as real_generate
from .http import get_bytes, get_text
from .models import Episode
from .source import resolve_text
from .state import State

ROOT = Path(__file__).resolve().parents[2]
GUIDES = ROOT / "guides"
TRANSCRIPTS = ROOT / "transcripts"
STATE = ROOT / "state.json"
PODCAST_FEED = "https://feeds.captivate.fm/traders-point/"
SITE_URL = "https://colsonrice.github.io/tpsermons"


@dataclass
class Deps:
    episodes: Callable[[], List[Episode]]
    resolve: Callable[[Episode], Optional[tuple]]
    links: Callable[[Episode], tuple]
    generate: Callable[..., object]


def run(deps: Deps, out_dir: Path, state_path: Path,
        episode: Optional[str] = None, force: bool = False) -> List[Path]:
    """Process pending episodes. Returns the guide files written."""
    out_dir = Path(out_dir)
    state = State(state_path)
    episodes = deps.episodes()
    by_guid = {e.guid: e for e in episodes}

    if episode:
        # --episode deliberately bypasses the state gate; that is its purpose.
        targets = [by_guid[episode]] if episode in by_guid else []
        if not targets:
            print("episode %s not found in feed" % episode, file=sys.stderr)
    else:
        pending = state.pending([e.guid for e in episodes])
        targets = [by_guid[g] for g in pending]

    written = []
    for ep in targets:
        resolved = deps.resolve(ep)
        if not resolved:
            print("no text source for %s; skipping" % ep.title, file=sys.stderr)
            continue
        text, source = resolved
        links, speaker = deps.links(ep)

        guide = deps.generate(ep, transcript=text, links=links, speaker=speaker, source=source)
        path = out_dir / render.guide_filename(guide)
        if path.exists() and not force:
            # Decision 2: a published guide is never silently regenerated.
            print("guide already exists: %s (use --force to overwrite)" % path.name,
                  file=sys.stderr)
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(render.render_markdown(guide), encoding="utf-8")
        # JSON is the durable render source: it lets the site rebuild every
        # guide's HTML when the design changes, with no regeneration spend.
        path.with_suffix(".json").write_text(
            json.dumps(render.guide_to_dict(guide), indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        state.mark(ep.guid)
        written.append(path)
        print("wrote %s (source: %s)" % (path.name, source))

    return written


# --- real fetchers -------------------------------------------------------

def _message_html(ep: Episode) -> Optional[str]:  # pragma: no cover - network
    if not ep.series:
        return None
    try:
        series_html = get_text(tpcc.series_url(ep.series))
        slug = tpcc.lookup_slug(series_html, ep.title)
        return get_text(tpcc.message_url(slug)) if slug else None
    except Exception:
        return None


def _live_deps() -> Deps:  # pragma: no cover - network
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    cache = {}

    def html_for(ep):
        if ep.guid not in cache:
            cache[ep.guid] = _message_html(ep)
        return cache[ep.guid]

    def pdf(ep):
        page = html_for(ep)
        url = tpcc.find_transcript_url(page) if page else None
        if not url:
            return None
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.pdf"
            p.write_bytes(get_bytes(url))
            return subprocess.run(["pdftotext", "-layout", str(p), "-"],
                                  capture_output=True, text=True).stdout or None

    def captions(ep):
        page = html_for(ep)
        vid = tpcc.find_video_id(page) if page else None
        return youtube.fetch_captions(vid) if vid else None

    def whisper(ep):
        return transcribe.transcribe_url(ep.mp3_url, client, get_bytes)

    def resolve(ep):
        # A cached transcript makes re-running a guide free -- otherwise every
        # prompt tweak re-transcribes the same audio through Whisper.
        cached = TRANSCRIPTS / ("%s.txt" % ep.guid)
        if cached.exists():
            text = cached.read_text(encoding="utf-8")
            head, _, rest = text.partition("\n")
            src = head[9:].strip() if head.startswith("#source:") else "cache"
            print("  using cached transcript (%s)" % src)
            return (rest.strip(), src)

        got = resolve_text(ep, pdf=pdf, captions=captions, whisper=whisper)
        if not got:
            return None
        TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
        cached.write_text("#source: %s\n%s" % (got.source, got.text), encoding="utf-8")
        return (got.text, got.source)

    def links(ep):
        page = html_for(ep)
        out = {"tpcc": "https://tpcc.org/messages", "podcast": ep.mp3_url}
        speaker = None
        if ep.series:
            try:
                slug = tpcc.lookup_slug(get_text(tpcc.series_url(ep.series)), ep.title)
                if slug:
                    out["tpcc"] = tpcc.message_url(slug)
            except Exception:
                pass
        if page:
            vid = tpcc.find_video_id(page)
            if vid:
                out["youtube"] = "https://youtu.be/%s" % vid
            speaker = tpcc.find_speaker(page)
        return out, speaker

    def gen(ep, transcript, links, speaker, source):
        return real_generate(ep, transcript, links, speaker, source, client)

    return Deps(
        episodes=lambda: feed.parse_feed(get_text(PODCAST_FEED)),
        resolve=resolve, links=links, generate=gen,
    )


def _write_site() -> None:  # pragma: no cover
    """Rebuild the index and every guide page from the committed JSON.

    Pages serves .md as text/markdown, so guides are published as HTML. JSON
    rather than markdown is the render source, so a design change reaches old
    guides without re-running the model.
    """
    guides = []
    for path in sorted(GUIDES.glob("*.json")):
        try:
            g = render.guide_from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (KeyError, ValueError) as exc:
            print("skipping %s: %s" % (path.name, exc), file=sys.stderr)
            continue
        (GUIDES / render.guide_filename(g, "html")).write_text(
            render.render_guide_page(g), encoding="utf-8")
        guides.append(g)
    (ROOT / "index.html").write_text(render.render_site(guides), encoding="utf-8")
    print("site rebuilt: %d guides" % len(guides))


def main(argv=None) -> int:  # pragma: no cover
    ap = argparse.ArgumentParser(prog="tpsermons")
    ap.add_argument("command", choices=["run", "seed", "diagnose", "pending"])
    ap.add_argument("--episode", help="episode GUID to process, bypassing state")
    ap.add_argument("--force", action="store_true", help="overwrite an existing guide")
    ap.add_argument("--quiet", action="store_true", help="suppress output (for pending)")
    args = ap.parse_args(argv)

    if args.command == "pending":
        # Exit 0 when work exists, 1 when idle, so the workflow can gate on it
        # without installing ffmpeg/poppler or touching the API.
        eps = feed.parse_feed(get_text(PODCAST_FEED))
        p = State(STATE).pending([e.guid for e in eps])
        if not args.quiet:
            print("%d pending" % len(p))
        return 0 if p else 1

    if args.command == "diagnose":
        return diagnose()

    if args.command == "seed":
        eps = feed.parse_feed(get_text(PODCAST_FEED))
        State(STATE).seed([e.guid for e in eps])
        print("seeded %d episodes; %d pending" % (len(eps), min(1, len(eps))))
        return 0

    written = run(_live_deps(), GUIDES, STATE, episode=args.episode, force=args.force)
    if not written:
        print("no new episodes")
        return 0

    _write_site()
    _email(written)
    return 0


def _email(written) -> None:  # pragma: no cover - network
    """Mail each new guide, if mail is configured.

    Never raises: the guide is already published and committed by this point,
    so a mail failure must not fail the run or block the deploy.
    """
    cfg = mail.MailConfig.from_env(os.environ)
    if cfg is None:
        print("mail not configured (set SMTP_USER, SMTP_PASSWORD, MAIL_TO); skipping")
        return
    for path in written:
        try:
            g = render.guide_from_dict(json.loads(
                path.with_suffix(".json").read_text(encoding="utf-8")))
            url = "%s/guides/%s" % (SITE_URL, render.guide_filename(g, "html"))
            subject, body_html, body_text = mail.render_email(g, url)
            mail.send(subject, body_html, body_text, cfg)
            print("emailed %r to %s" % (subject, ", ".join(cfg.to)))
        except Exception as exc:
            print("email failed for %s: %s" % (path.name, exc), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
