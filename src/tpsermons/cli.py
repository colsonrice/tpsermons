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

from . import feed, render, tpcc, transcribe, youtube
from .generate import generate as real_generate
from .http import get_bytes, get_text
from .models import Episode
from .source import resolve_text
from .state import State

ROOT = Path(__file__).resolve().parents[2]
GUIDES = ROOT / "guides"
STATE = ROOT / "state.json"
PODCAST_FEED = "https://feeds.captivate.fm/traders-point/"


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
        got = resolve_text(ep, pdf=pdf, captions=captions, whisper=whisper)
        return (got.text, got.source) if got else None

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
    """Rebuild the index and a readable HTML page for every guide.

    Guides are authored as markdown, but Pages serves .md as text/markdown --
    a group leader clicking that link gets raw YAML front matter. Each guide
    is therefore also published as HTML, and the index links to that.
    """
    import re
    guides = []
    for path in sorted(GUIDES.glob("*.md")):
        md = path.read_text(encoding="utf-8")
        path.with_suffix(".html").write_text(render.render_guide_page(md), encoding="utf-8")
        fm = dict(re.findall(r"^(\w+): (.*)$", md.split("---")[1], re.M)) if "---" in md else {}
        guides.append(type("G", (), {
            "title": fm.get("title", path.stem), "date": fm.get("date", ""),
            "series": fm.get("series"), "passage": fm.get("passage")})())
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
    if written:
        _write_site()
    else:
        print("no new episodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
