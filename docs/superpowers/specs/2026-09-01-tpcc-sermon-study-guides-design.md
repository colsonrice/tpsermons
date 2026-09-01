# TPCC Sermon Study Guides — Design

**Date:** 2026-09-01
**Status:** Approved

## Problem

Traders Point Christian Church (TPCC) publishes a sermon every Sunday. Until
early 2026 they also published a one-page "Group Message Guide" for each
message — the discussion material a small group leader needs for the week.
They stopped. Guides are present on messages through February 2026 and absent
on every message from August 2026.

This project restores that artifact: an automated weekly job that ingests each
new sermon and produces a small-group discussion guide in TPCC's own format.

## Goals

- Produce a small-group discussion guide for each new sermon, automatically.
- Publish guides to a browsable site so they can be shared with group leaders.
- Prefer TPCC's own source material over anything we synthesize.
- Run unattended on a schedule with no local machine involved.

## Non-goals

- Republishing TPCC sermon transcripts or audio.
- Personal/daily-devotional guides, sermon recaps, or notes formats.
- Regenerating a guide once published (see "Transcript lag" below).
- Archive backfill. Explicitly deferred; see "Backfill and first run".

## Research findings

All of the following was verified empirically against live sources on
2026-09-01, not assumed.

### Sources evaluated

| Source | Verdict |
|---|---|
| TPCC Group Message Guide (PDF) | **Discontinued.** Present Jan/Feb 2026 and earlier; absent Aug 2026. Valuable as format exemplars. |
| TPCC message transcript (PDF) | **Best text source.** Exists for every message. ~8-day lag. |
| Podcast MP3 (Captivate) | **Only same-week source.** Reliable, no bot-blocking. |
| YouTube auto-captions | **Rejected.** See below. |

### YouTube is not a viable transcript source

Sermon videos do carry English auto-generated (ASR) caption tracks. However:

- Fetching the signed `/api/timedtext` caption URL returns **HTTP 200 with a
  zero-byte body** on every format variant tried (`json3`, `srv3`, `vtt`,
  raw), from a residential IP. YouTube now gates this endpoint behind a
  proof-of-origin token.
- Libraries that route around this (`youtube-transcript-api`, `yt-dlp`) use
  the InnerTube API, which is routinely IP-blocked from GitHub Actions
  datacenter ranges. Working around *that* requires a paid residential proxy.
- Even when it works, ASR captions arrive with no punctuation, no casing and
  no paragraph breaks. That is materially worse input than either alternative.

YouTube is therefore used only to resolve a video link for the guide header.

### Transcript lag is ~8 days

TPCC transcript PDFs are produced in Canva and posted the following weekend.
Measured from PDF `CreationDate`:

| Sermon date | Transcript created | Lag |
|---|---|---|
| Aug 22 | Aug 30 | 8 days |
| Aug 15 | Aug 23 | 8 days |
| Aug 8  | Aug 17 | 9 days |
| Aug 1  | Aug 9  | 8 days |

**Consequence:** a Monday job will never find an official transcript for the
sermon that just aired. Fresh guides must be built from our own transcription.
The cascade still pays off for archive backfill, where transcripts always exist.

### Audio sizing

Across 224 episodes: median 45 min, longest 68.5 min at 192 kbps (98.6 MB).
Re-encoded to 16 kHz mono 32 kbps, the longest episode is **16.4 MB** — under
OpenAI's 25 MB upload cap. **No chunking logic is required.**

## Decisions

1. **Guide covers the most recent sermon**, transcribed by us. Accepted
   tradeoff: ASR text can garble proper nouns and scripture citations.
2. **No regeneration.** A published guide is final, even after the official
   transcript later appears. Chosen for pipeline simplicity.
3. **Source cascade retained** — official transcript is used when present.
   In practice this means Whisper for new sermons, official text for backfill.
4. **Public repo, guides only.** Transcripts are runner-local build artifacts,
   gitignored, never uploaded. Every guide links back to TPCC's message page.
5. **No TPCC material in the prompt.** The guide format is captured as our own
   prose description of section shape, question count and register, checked in
   at `prompts/guide_format.md`. No TPCC PDFs are committed or sent to the
   model. This resolves a contradiction in an earlier draft, which called for
   archived TPCC guides as prompt exemplars while also forbidding their
   storage; it also removes a dependency on PDFs that are being retired.
6. **Reference only, no verse text.** Guides carry the scripture reference
   (e.g. `Mark 9:30-50`), never the verse text. Modern translations are
   separately licensed and the site is public. Leaders use their own Bible.

## Schedule and models

- Trigger: GitHub Actions `schedule`, `cron: '0 13 * * 1'` — Mondays 13:00 UTC
  (09:00 ET during EDT). Also `workflow_dispatch` for manual runs.
- Feed is polled once per run. No other polling.
- Transcription: `gpt-4o-mini-transcribe` (fallback `whisper-1`), ~$0.003/min.
- Generation: `gpt-4o`. Both pinned as constants, overridable by env var.
- The ~$0.20/sermon estimate assumes these two models at a 45-minute median.

## Architecture

```
Captivate RSS ──> discover ──> source ──> generate ──> publish
                     |            |           |            |
              new episode?    transcript   model +     markdown +
              else exit 0      cascade    exemplars   Pages site
```

**discover** — poll the Captivate feed; compare GUIDs against committed
`state.json`. No new episode is a clean no-op exit, not a failure. Resolves
cross-links: YouTube video (title match against channel feed) and TPCC message
page (slug match against the series page).

**source** — fetch the TPCC message page; use the official transcript PDF if
present (`pdftotext`); otherwise ffmpeg-downsample the MP3 and transcribe in a
single API call.

**generate** — assemble prompt, call model, validate output shape.

**publish** — write markdown, render site, commit.

## Modules

| Module | Responsibility | Key boundary |
|---|---|---|
| `feed.py` | Captivate RSS -> `Episode` records | Pure parse; takes XML text |
| `tpcc.py` | Message page -> transcript URL, guide URL, canonical link | Pure parse; takes HTML text |
| `transcribe.py` | ffmpeg re-encode + transcription call | Takes a path, returns text |
| `generate.py` | Prompt assembly, model call, validation | Takes transcript, returns `Guide` |
| `render.py` | `Guide` -> markdown + site HTML | No network |

Network access is confined to thin fetch wrappers so every parser is testable
offline against saved fixtures.

## Data model

`Episode`: guid, title, pub_date, mp3_url, duration, series, passage, slug.

The passage is parsed from the podcast title, which reliably encodes it —
e.g. `Presence Over Position | The Urgent Kingdom | Mark 9:30-50`. It is
carried into the guide header as a reference and supplied to the model to
anchor it against ASR citation errors. Verse text is never fetched (Decision 6).

`state.json`: processed GUIDs. Provides idempotency.

`Guide` — the boundary type between `generate.py` and `render.py`. The model
returns JSON conforming to this shape, and validation is exact:

| Field | Type | Constraint |
|---|---|---|
| `title`, `series`, `speaker`, `date`, `passage` | str | required, non-empty |
| `links` | obj | `tpcc` required; `youtube`, `podcast` optional |
| `recap` | str | required, 60-150 words |
| `discuss` | list | **exactly 3** blocks |
| `discuss[].heading` | str | required, non-empty |
| `discuss[].questions` | list[str] | **2-3** questions per block |
| `take_action` | str | required, 40-120 words |
| `reflections` | list[str] | **exactly 3** |

Validation failure means: any missing required field, any count outside these
bounds, or any field containing placeholder text (`TODO`, `TBD`, `[`, `...`).

## Guide format

Mirrors TPCC's discontinued house format so leaders recognize it: a header
block (title, series, speaker, date, passage, links), a short recap, a
`DISCUSS` section of three themed question blocks, and a `TAKE ACTION`
section closing with journaling reflections.

The format is described in our own words in `prompts/guide_format.md` and
committed to the repo. No TPCC guide PDFs are stored or sent to the model
(Decision 5). All guide prose is generated from the sermon transcript.

## Site

GitHub Pages built from committed markdown. Current week's guide on the
landing page; archive grouped by series below. Public repo, so Actions
minutes and Pages are free. `OPENAI_API_KEY` is the only secret.

## Backfill and first run

Backfill is **not in scope**. The feed holds 224 episodes, and an empty
`state.json` would otherwise cause the first run to process all of them.

Bootstrap: a one-time `seed` command writes every current feed GUID into
`state.json` *except the most recent*, so the first scheduled run produces
exactly one guide. The repo ships with `state.json` already seeded.

## Failure handling

- No new episode -> exit 0, no commit.
- Cross-link unresolved (no YouTube title match, or no TPCC slug match) ->
  log a warning and omit that link from the header. Never fails the run. The
  TPCC link is reconstructed from the slug if the series-page match fails.
- Transcription or generation failure -> retry once, then fail loudly and
  open an issue. Never commit a partially built guide.
- Model output failing shape validation -> retry once, then fail.
- All writes gated on `state.json` so a re-run is safe.

## Testing

Offline unit tests against saved fixtures for feed parsing, slug matching and
PDF text extraction.

**Quality benchmark:** a *manual* evaluation activity, not shipped code and
not in the module table. Several dozen back-catalog sermons have both an
official transcript and an official TPCC group guide, so a guide generated
from one can be read against the real published one to sanity-check output
quality before launch. Reference PDFs stay local and uncommitted.

## Cost

~$0.15 transcription + ~$0.05 generation = **~$0.20 per sermon (~$10/year)**.
Archive backfill is near-free, since official transcripts already exist.

## Legal posture

Guides are derivative work: original discussion questions plus summary. They
are published. TPCC's transcripts and audio are not republished, not
committed, and not exposed as build artifacts. Each guide attributes and links
to TPCC's own message page and video.
