# TPCC Sermon Study Guides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily GitHub Actions job that turns each new TPCC sermon into a small-group discussion guide and publishes it to a GitHub Pages site.

**Architecture:** Four stages — `discover` (poll the Captivate podcast feed, diff against `state.json`, resolve cross-links), `source` (walk the cascade: official TPCC transcript PDF > YouTube message-only captions > Whisper on the MP3), `generate` (model writes prose only; code injects all metadata), `publish` (markdown + static site + commit). Every parser is a pure function over text so the whole suite runs offline against saved fixtures.

**Tech Stack:** Python 3.9+, `youtube-transcript-api`, `openai`, `feedparser`-free stdlib XML parsing, `pdftotext` (poppler), ffmpeg, pytest, GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-01-tpcc-sermon-study-guides-design.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `src/tpsermons/models.py` | `Episode`, `Guide`, `SourcedText` dataclasses. No logic. |
| `src/tpsermons/titles.py` | Parse `Title \| Series \| Passage`; sermon-vs-clip detection. Shared by feed and youtube. |
| `src/tpsermons/feed.py` | Captivate RSS text -> `list[Episode]`. Pure. |
| `src/tpsermons/youtube.py` | Channel RSS -> message-only video id; caption fetch; cue normalization. |
| `src/tpsermons/tpcc.py` | Message page HTML -> transcript URL, speaker. Pure parse. |
| `src/tpsermons/transcribe.py` | ffmpeg re-encode + OpenAI transcription. |
| `src/tpsermons/source.py` | The Decision 3 cascade. Returns `SourcedText`. |
| `src/tpsermons/generate.py` | Prompt assembly, model call, shape validation. |
| `src/tpsermons/render.py` | `Guide` -> markdown; guides -> site HTML. Pure. |
| `src/tpsermons/state.py` | `state.json` load/save/seed. Single writer. |
| `src/tpsermons/cli.py` | Entry point wiring the stages; `run`, `seed` commands. |
| `prompts/guide_format.md` | Our own prose description of the guide format (Decision 5). |
| `.github/workflows/daily.yml` | Daily cron + `workflow_dispatch`. |

Network access lives only in `youtube.py`, `transcribe.py`, `source.py` fetch helpers and `cli.py`. Everything else is pure and fixture-testable.

---

### Task 1: Scaffolding and fixtures

**Files:**
- Create: `pyproject.toml`, `src/tpsermons/__init__.py`, `tests/__init__.py`, `.gitignore`
- Create: `tests/fixtures/` (real captured data)

- [ ] **Step 1: Create the package layout and pyproject**

```toml
[project]
name = "tpsermons"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["youtube-transcript-api>=1.0", "openai>=1.40"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 2: Capture real fixtures**

Save live responses as fixtures so tests never hit the network:

```bash
mkdir -p tests/fixtures
curl -sL "https://feeds.captivate.fm/traders-point/" -o tests/fixtures/podcast.xml
curl -sL "https://www.youtube.com/feeds/videos.xml?channel_id=UCYlj586dgrLdWZhD_znqQhg" -o tests/fixtures/channel.xml
curl -sL "https://tpcc.org/messages/help-my-unbelief" -o tests/fixtures/message_page.html
```

- [ ] **Step 3: .gitignore — never commit TPCC source material (Decision 4)**

```
__pycache__/
*.pyc
.venv/
work/
*.mp3
*.pdf
.env
```

- [ ] **Step 4: Verify pytest collects**

Run: `python -m pytest -q`
Expected: `no tests ran` (exit 5), not an import error.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: scaffold package, pytest config and real fixtures"
```

---

### Task 2: Title parsing and sermon detection

The three-segment title rule drives both passage extraction and non-sermon filtering (spec: Data model).

**Files:**
- Create: `src/tpsermons/titles.py`, `tests/test_titles.py`

- [ ] **Step 1: Write the failing tests**

```python
from tpsermons.titles import parse_title, is_sermon_title

def test_parses_three_segment_title():
    p = parse_title("Presence Over Position | The Urgent Kingdom | Mark 9:30-50")
    assert p.title == "Presence Over Position"
    assert p.series == "The Urgent Kingdom"
    assert p.passage == "Mark 9:30-50"

def test_non_sermon_titles_are_rejected():
    assert not is_sermon_title("Does God send people to hell?")           # clip
    assert not is_sermon_title("Have We Lost the Fear of God? | Taking Ground Podcast")
    assert not is_sermon_title("Enough | The Urgent Kingdom | Mark 8:1-13 | Full Gathering")
    assert is_sermon_title("Enough | The Urgent Kingdom | Mark 8:1-13")

def test_unparseable_title_yields_none_fields_not_an_error():
    p = parse_title("Some Talk")
    assert p.title == "Some Talk" and p.series is None and p.passage is None
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_titles.py -q` → ImportError.

- [ ] **Step 3: Implement**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

FULL_GATHERING = "full gathering"

@dataclass(frozen=True)
class ParsedTitle:
    title: str
    series: Optional[str] = None
    passage: Optional[str] = None

def _segments(raw: str) -> list:
    return [s.strip() for s in raw.split("|") if s.strip()]

def parse_title(raw: str) -> ParsedTitle:
    segs = _segments(raw)
    if len(segs) == 3:
        return ParsedTitle(segs[0], segs[1], segs[2])
    return ParsedTitle(segs[0] if segs else raw.strip())

def is_sermon_title(raw: str) -> bool:
    segs = _segments(raw)
    if len(segs) != 3:
        return False
    return segs[-1].lower() != FULL_GATHERING
```

- [ ] **Step 4: Run tests** → PASS.
- [ ] **Step 5: Commit** — `git commit -am "feat: title parsing and sermon detection"`

---

### Task 3: Models

**Files:** Create `src/tpsermons/models.py`, `tests/test_models.py`

- [ ] **Step 1: Test that Guide rejects out-of-bounds shapes**

```python
import pytest
from tpsermons.models import Guide, DiscussBlock, ValidationError

def _blocks(n=3, q=2):
    return [DiscussBlock(heading=f"H{i}", questions=[f"Q{j}" for j in range(q)]) for i in range(n)]

def valid(**kw):
    base = dict(title="T", series="S", speaker=None, date="2026-08-30", passage="Mark 9",
                links={"tpcc": "https://tpcc.org/messages/x"},
                recap=" ".join(["word"]*80), discuss=_blocks(),
                take_action=" ".join(["word"]*60), reflections=["a","b","c"], source="youtube")
    base.update(kw); return Guide(**base)

def test_valid_guide_passes():
    valid().validate()

@pytest.mark.parametrize("kw", [
    dict(discuss=_blocks(n=2)), dict(discuss=_blocks(q=1)), dict(discuss=_blocks(q=4)),
    dict(reflections=["a","b"]), dict(recap="too short"),
])
def test_invalid_shapes_rejected(kw):
    with pytest.raises(ValidationError):
        valid(**kw).validate()

def test_placeholder_tokens_rejected_but_ellipsis_and_inaudible_allowed():
    with pytest.raises(ValidationError):
        valid(recap=" ".join(["word"]*79 + ["TODO"])).validate()
    valid(recap=" ".join(["word"]*78) + " and so on ... [inaudible]").validate()
```

- [ ] **Step 2: Run → fails.**
- [ ] **Step 3: Implement** `Episode`, `DiscussBlock`, `Guide`, `SourcedText`, `ValidationError`. Placeholder detection matches whole tokens `TODO|TBD|FIXME|XXX|Lorem` (case-insensitive, `\b`-bounded) plus `\[insert[^\]]*\]`. Bare `...` and `[inaudible]` must pass.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit.**

---

### Task 4: Captivate feed parsing

**Files:** Create `src/tpsermons/feed.py`, `tests/test_feed.py`

- [ ] **Step 1: Tests against `tests/fixtures/podcast.xml`**

```python
def test_parses_episodes_from_real_feed():
    eps = parse_feed(FIXTURE.read_text())
    assert len(eps) > 200
    e = eps[0]
    assert e.guid and e.mp3_url.endswith(".mp3") and e.pub_date.year == 2026

def test_episodes_are_newest_first():
    eps = parse_feed(FIXTURE.read_text())
    assert eps[0].pub_date >= eps[1].pub_date

def test_non_sermon_items_are_excluded():
    for e in parse_feed(FIXTURE.read_text()):
        assert e.passage is not None
```

- [ ] **Step 2-5:** Fail → implement with `xml.etree.ElementTree` (skip items failing `is_sermon_title`) → pass → commit.

---

### Task 5: YouTube video selection

**Files:** Create `src/tpsermons/youtube.py`, `tests/test_youtube.py`

- [ ] **Step 1: Test exact-match selection against `channel.xml`**

```python
def test_selects_message_only_cut_not_full_gathering():
    vid = find_video(CHANNEL.read_text(), "Presence Over Position | The Urgent Kingdom | Mark 9:30-50")
    assert vid == "-F6w9h2Jpg8"       # not itp0FIVGEUs (Full Gathering)

def test_returns_none_when_absent():
    assert find_video(CHANNEL.read_text(), "Nonexistent | Series | Mark 1:1") is None
```

Matching is exact equality after whitespace collapse + casefold (spec: Title matching).

- [ ] **Steps 2-5:** Fail → implement → pass → commit.

---

### Task 6: Caption retrieval and normalization

**Files:** Modify `src/tpsermons/youtube.py`; create `tests/fixtures/cues.json`, extend `tests/test_youtube.py`

- [ ] **Step 1: Save a real cue fixture**

```bash
python -c "from youtube_transcript_api import YouTubeTranscriptApi as A; import json; \
print(json.dumps([s.text for s in A().fetch('cAmHuBCSFvo')]))" > tests/fixtures/cues.json
```

- [ ] **Step 2: Test normalization (pure, offline)**

```python
def test_normalize_joins_cues_and_strips_markers():
    cues = json.loads(CUES.read_text())
    text = normalize_cues(cues)
    assert "[music]" not in text.lower() and "[applause]" not in text.lower()
    assert 7000 < len(text.split()) < 8000       # real sermon: ~7607 words
    assert "  " not in text
```

- [ ] **Steps 3-5:** Implement `normalize_cues` (join with space, strip `\[[a-z ]+\]`, collapse whitespace) and a thin `fetch_captions(video_id)` wrapper returning `None` on any exception. Pass → commit.

---

### Task 7: TPCC message page parsing

**Files:** Create `src/tpsermons/tpcc.py`, `tests/test_tpcc.py`

- [ ] **Step 1: Tests against `message_page.html`**

```python
def test_finds_transcript_url_when_present():
    assert "GetFile.ashx" in find_transcript_url(HTML.read_text())

def test_extracts_speaker_from_description_prose():
    assert find_speaker(HTML.read_text()) == "Chad Lunsford"

def test_speaker_none_when_pattern_absent():
    assert find_speaker("<html><body>nothing</body></html>") is None
```

Speaker regex targets `In this message, ...<Pastor|Minister|...> <Name> (preaches|teaches|shares)` — best-effort, never fatal (spec: Data model).

- [ ] **Steps 2-5:** Fail → implement → pass → commit.

---

### Task 8: State management

**Files:** Create `src/tpsermons/state.py`, `tests/test_state.py`

- [ ] **Step 1: Tests**

```python
def test_seed_marks_all_but_most_recent(tmp_path):
    st = State(tmp_path/"state.json"); st.seed(["g1","g2","g3"])   # newest first
    assert not st.is_processed("g1") and st.is_processed("g2") and st.is_processed("g3")

def test_pending_returns_oldest_first(tmp_path): ...
def test_roundtrip_persists(tmp_path): ...
```

- [ ] **Steps 2-5:** Implement → pass → commit.

---

### Task 9: The source cascade

**Files:** Create `src/tpsermons/source.py`, `tests/test_source.py`

- [ ] **Step 1: Tests with injected fakes — no network**

```python
def test_prefers_official_transcript_when_present():
    got = resolve_text(EP, pdf=lambda e: "official", captions=lambda e: "yt", whisper=lambda e: "w")
    assert got.text == "official" and got.source == "transcript_pdf"

def test_falls_back_to_captions_when_no_pdf():
    got = resolve_text(EP, pdf=lambda e: None, captions=lambda e: "yt", whisper=lambda e: "w")
    assert got.source == "youtube_captions"

def test_falls_through_to_whisper_when_captions_unavailable():
    got = resolve_text(EP, pdf=lambda e: None, captions=lambda e: None, whisper=lambda e: "w")
    assert got.source == "whisper"

def test_never_defers_waiting_on_captions():
    # spec: availability policy — a missing caption track costs money, not a delay
    got = resolve_text(EP, pdf=lambda e: None, captions=lambda e: None, whisper=lambda e: "w")
    assert got.text == "w"
```

Dependency injection is what makes the cascade testable offline; `cli.py` supplies the real fetchers.

- [ ] **Steps 2-5:** Implement → pass → commit.

---

### Task 10: Transcription fallback

**Files:** Create `src/tpsermons/transcribe.py`, `tests/test_transcribe.py`

- [ ] **Step 1: Test the ffmpeg command shape (no audio needed)**

```python
def test_ffmpeg_args_downsample_to_mono_16k_32kbps():
    args = ffmpeg_args("in.mp3", "out.mp3")
    assert "-ac" in args and args[args.index("-ac")+1] == "1"
    assert "-ar" in args and args[args.index("-ar")+1] == "16000"
    assert "-b:a" in args and args[args.index("-b:a")+1] == "32k"
```

Rationale in spec: this keeps the longest sermon (68.5 min) at ~16.4 MB, under the 25 MB cap, so no chunking is needed.

- [ ] **Steps 2-5:** Implement `ffmpeg_args` + `transcribe(path)` calling `gpt-4o-mini-transcribe`, retrying once against `whisper-1`. Pass → commit.

---

### Task 11: Guide generation

**Files:** Create `src/tpsermons/generate.py`, `prompts/guide_format.md`, `tests/test_generate.py`

- [ ] **Step 1: Write `prompts/guide_format.md`** — our own prose description of the format (Decision 5: no TPCC PDFs). Describes: a short recap, exactly three `DISCUSS` blocks each with a heading and 2-3 questions, a `TAKE ACTION` paragraph, exactly three journaling reflections. Register: warm, plain, for a mixed-maturity small group.

- [ ] **Step 2: Test that code injects metadata and the model never supplies links**

```python
def test_model_prose_is_merged_with_code_supplied_metadata():
    payload = {"recap": " ".join(["w"]*80), "discuss": [...], "take_action": ..., "reflections": [...]}
    g = build_guide(EP, payload, links={"tpcc": "https://tpcc.org/messages/x"}, speaker="Chad Lunsford")
    assert g.links["tpcc"].startswith("https://tpcc.org")
    assert g.title == EP.title

def test_model_supplied_links_are_ignored():
    payload = {..., "links": {"tpcc": "https://evil.example"}}
    g = build_guide(EP, payload, links={"tpcc": "https://tpcc.org/messages/x"}, speaker=None)
    assert "evil" not in g.links["tpcc"]        # hallucinated URLs structurally impossible
```

- [ ] **Steps 3-5:** Implement (JSON response format, one retry on validation failure) → pass → commit.

---

### Task 12: Rendering

**Files:** Create `src/tpsermons/render.py`, `tests/test_render.py`

- [ ] **Step 1: Tests** — markdown contains title, passage, all three headings, all reflections; omits the speaker line when `speaker is None`; omits the YouTube link when absent but always renders the TPCC link; records the source in front matter.
- [ ] **Steps 2-5:** Implement markdown + a minimal static site (`index.html` = latest guide, archive grouped by series) → pass → commit.

---

### Task 13: CLI wiring

**Files:** Create `src/tpsermons/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: Tests**

```python
def test_no_new_episode_is_a_clean_noop(): assert run(...) == 0     # not a failure
def test_multiple_pending_processed_oldest_first(): ...
def test_episode_flag_bypasses_state_gate(): ...
def test_episode_flag_refuses_overwrite_without_force(): ...
```

- [ ] **Steps 2-5:** Implement `run` / `seed` with `--episode`, `--force` → pass → commit.

---

### Task 14: GitHub Actions workflow

**Files:** Create `.github/workflows/daily.yml`

- [ ] **Step 1: Write the workflow**

```yaml
on:
  schedule: [{cron: '0 13 * * *'}]     # daily 13:00 UTC = 09:00 ET
  workflow_dispatch:
    inputs:
      episode: {description: 'Episode GUID to re-run', required: false}
      force:   {description: 'Overwrite existing guide', type: boolean, default: false}
permissions:
  contents: write
  issues: write
```

Steps: checkout → setup-python → `apt-get install -y poppler-utils ffmpeg` → `pip install -e .` → run → commit guides if changed → deploy Pages. On failure, open an issue.

- [ ] **Step 2: Validate YAML parses** — `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/daily.yml'))"`
- [ ] **Step 3: Commit.**

---

### Task 15: Seed state and first real run

- [ ] **Step 1:** `python -m tpsermons.cli seed` → writes `state.json` with all GUIDs but the newest.
- [ ] **Step 2:** Verify exactly one episode is pending.
- [ ] **Step 3:** Run end-to-end with a real key; inspect the generated guide by hand against the spec's format.
- [ ] **Step 4:** Commit the seeded state and the first guide.

---

## Verification

Run before declaring done:

```bash
python -m pytest -q          # all green, no network
```

Then confirm by hand: the generated guide has three DISCUSS blocks, three reflections, a TPCC link, and correct passage — and that no `.pdf`, `.mp3` or transcript text is tracked by git.
