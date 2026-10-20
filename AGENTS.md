# Notes for AI coding agents (Codex, Claude Code, etc.)

**Read first:** [`docs/vision/VISION.md`](docs/vision/VISION.md) (the owner's vision and
non-negotiables) and [`docs/vision/IDEAS_LOG.md`](docs/vision/IDEAS_LOG.md) (dated idea log).
Before touching any chart, color, text, or AI prompt, read
[`docs/DATA_STORYTELLING_GUIDE.md`](docs/DATA_STORYTELLING_GUIDE.md): the research-based rules
for making everything understandable at first glance. Its "Rules for the writer" block is loaded
into the AI's instructions on every call, so edit it there.
When the owner shares a new idea or preference, **add it to the top of `IDEAS_LOG.md`**
and update `VISION.md` if it changes the direction. The owner switches between Claude
Code and Codex, so these files are the shared memory.

## Owner preferences
- **Ship every change automatically.** When you finish a change: run the tests, commit,
  push, open a pull request into `main`, and merge it right away (no need to ask). The
  owner's copy of Tally updates itself from `main` every time it opens. Never merge if
  the tests fail; fix them first or explain what's wrong.
- Never use the em dash character in user-facing text, docs, or generated wording.
  Use a comma, period, or a simple hyphen.
- Simplicity first. Plain language. Calm visuals. Nothing that looks like "AI slop".
- Accuracy is the top priority: never show a pattern that isn't statistically backed.

## How it's built
- `tally/` Python package (FastAPI server, run with `uv run python -m tally`).
  - `loader.py` reads + cleans files and writes a plain-English cleaning log.
  - `profile.py` decides each column's role (measure, category, time, id, text...).
  - `insights.py` the statistics engine. All maths lives here. Every candidate has a
    p-value (or is an exact fact), is corrected with Benjamini-Hochberg across the
    whole run, and must pass an effect-size floor. `select()` ranks and orders the story.
  - `narrate.py` lets the local LLM reword findings. `numbers_ok()` rejects any text
    with numbers the engine didn't produce. Keep this guard.
  - `chat.py` "Ask Tally": LLM with calculator tools over the real DataFrame.
  - `analysis.py` pipeline -> report JSON. `history.py` saves reports to the user data dir.
  - `ollama.py` tiny Ollama client + recommended models list.
- `tally/static/` the frontend. No build step: plain JS files that attach to
  `window.Tally`. ECharts, html2canvas and jsPDF are vendored in `static/vendor/`
  so everything works offline. `report-view.js` must stay server-independent
  because it is inlined into exported interactive HTML files.
- `launchers/` start scripts (Mac, Windows, Linux) + `update.py` (self-update from
  GitHub) + app icons. `Start Tally (Mac).command`, `Start Tally (Windows).bat` and
  `Tally.app` at the repo root are what users double-click.
- `install/` one-line installers. `samples/` demo data with planted patterns.

## Checks before you commit
```
uv run --group dev pytest -q
```
`tests/test_engine.py::test_pure_noise_produces_no_findings` is the most important
test: random data must never produce "discoveries". Don't weaken it.

## Design rules for charts
One highlight colour (data blue) for the point of the story, grey for the rest,
hairline grids, values at bar tips, tooltip on everything, a table view for every
chart, never dual axes, light and dark themes.
