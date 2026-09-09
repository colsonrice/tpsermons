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

Cost is roughly **$0.20 per sermon (~$10/year)**.

YouTube captions would make this nearly free, and they work perfectly from a
home connection — but **YouTube blocks GitHub's datacenter IPs**, confirmed on
two independent CI runs. So the scheduled path is Whisper. The caption branch
stays because it costs nothing when it fails and is used for local re-runs.

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

## Structure of a guide

The group stays together throughout — no breakouts, no time limits on
questions. Five movements: **Open** (one low-stakes question), **Read** (one or
two short verse ranges, never a whole chapter, plus one observation question),
**Discuss** (three questions with follow-up probes), **Get Honest** (what will
actually get in the way), and **Commit** (one specific action, plus what the
group will ask each other next week).

## What is and isn't published

Guides are original work — discussion questions and framing — and they are
published to the site. Sermon **audio** is never stored. Transcripts are cached
under `transcripts/` so that re-running a guide costs nothing; they are not
linked from the site, and can be removed at any time by deleting the directory
and adding it back to `.gitignore`. Every guide links back to the church's own
message page and video.
