# TPCC Sermon Study Guides

Generates a small-group discussion guide from each new Traders Point Christian
Church sermon and publishes it to a browsable site.

Traders Point used to publish a one-page "Group Message Guide" alongside each
message. They stopped sometime after February 2026. This restores it.

## How it works

```
Captivate podcast feed ──> discover ──> source ──> generate ──> publish
                                          │
                    official transcript PDF (when posted, ~8-day lag)
                         └─> YouTube message-only captions   ← normal path
                              └─> Whisper on the MP3         ← paid fallback
```

Runs daily at 09:00 ET. Daily rather than Monday-only because the feed
publishes Sun 48 / Mon 8 / Tue 3 / Wed 1 across the last 60 episodes — a
Monday-only job would silently skip about one week in five.

Cost is roughly **$0.05 per sermon** (guide generation only). Transcription is
free unless YouTube is unavailable, in which case that week costs about $0.20.

## Setup

1. Add `OPENAI_API_KEY` to the repository secrets.
2. Enable GitHub Pages with "GitHub Actions" as the source.
3. That's it — the daily workflow does the rest.

## Local use

```bash
python -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/python -m pytest          # 64 tests, no network required
```

```bash
OPENAI_API_KEY=sk-... ./.venv/bin/python -m tpsermons.cli run
```

Re-run a specific episode (bypasses the processed-state gate):

```bash
./.venv/bin/python -m tpsermons.cli run --episode <guid> --force
```

Requires `ffmpeg` and `pdftotext` (poppler) only for the fallback paths.

## What is and isn't published

Guides are original work — a summary plus discussion questions — and they are
published. TPCC's sermon transcripts and audio are **not**: they are fetched at
runtime, used, and discarded, never committed and never uploaded as build
artifacts. Every guide links back to the church's own message page and video.
