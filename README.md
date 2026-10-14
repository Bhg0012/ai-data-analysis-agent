<p align="center"><img src="launchers/icons/tally.png" width="96" alt="Tally"></p>

<h1 align="center">Tally</h1>
<p align="center"><b>Drop in a spreadsheet. Tally finds the story.</b><br>
A friendly data analyst that runs on your own computer.</p>

---

Tally is for people who have a spreadsheet and **no idea where to start**. You drop
in a CSV or Excel file. Tally reads every row, tidies up the mess, tests every
pattern with real statistics, and gives you a short, clear story: a few charts
that actually matter, explained in plain English, with gentle ideas for what to do next.

- **Accurate, not random.** Every finding is checked with a proper statistical test,
  corrected for the number of tests run, and must be big enough to matter. If
  nothing real turns up, Tally says so instead of making something up.
- **The AI never does the maths.** A local AI (via [Ollama](https://ollama.com))
  only rewords proven findings. Any sentence with a number the statistics engine
  didn't produce is thrown away.
- **Private.** Everything runs on your computer. Nothing is uploaded anywhere.
- **Simple.** One idea per chart, calm visuals, a "See the numbers" table under
  every chart, and "How do we know?" in plain words.
- **Save and share.** PDF, PNG, or an interactive file that opens in any browser.
  Every report is kept in **History**.
- **Ask questions.** "Which store sold the most?" Tally calculates the answer from
  your actual rows and shows a chart.

## Install

See **[HOW TO INSTALL.txt](HOW%20TO%20INSTALL.txt)** for step-by-step instructions
(including setting up the AI). Short version:

| | |
|---|---|
| **Mac** | Paste into Terminal: `curl -fsSL https://raw.githubusercontent.com/bhg0012/ai-data-analysis-agent/main/install/install-mac.sh \| bash`<br>or double-click **Start Tally (Mac).command** |
| **Windows** | Paste into PowerShell: `irm https://raw.githubusercontent.com/bhg0012/ai-data-analysis-agent/main/install/install-windows.ps1 \| iex`<br>or double-click **Start Tally (Windows).bat** |

Tally updates itself from GitHub every time it starts. Python is installed
automatically (via [uv](https://docs.astral.sh/uv/)) the first time.

### Recommended AI models

| Model | Download | Good for |
|---|---|---|
| `qwen3.5:9b` | ~7 GB | **Default.** Best balance of clear writing and reliable tool use (16 GB RAM) |
| `gpt-oss:20b` | ~14 GB | Strongest reasoning if you have 24 GB+ RAM |
| `gemma4:e4b` | ~7 GB | Friendly writing, good on laptops |
| `qwen3.5:4b` | ~3.5 GB | Older or 8 GB machines |

You can download any of these from inside Tally (Settings).

## What Tally looks for

Trends over time, unusual spikes, day-of-week and seasonal rhythms, differences
between groups, where totals come from, numbers that move together, categories
that overlap, and extreme values. It also cleans as it goes: finds the real
header under title rows, removes Total rows, turns "$1,200" and "45%" into numbers,
recognises dates, merges "north" / "North", and lists every fix it made.

## For developers

```bash
uv run python -m tally            # start the app (opens a window)
uv run --group dev pytest -q      # run the tests
```

- `tally/` Python backend (FastAPI, pandas, scipy). The statistics engine is `tally/insights.py`.
- `tally/static/` frontend, no build step (ECharts, html2canvas, jsPDF vendored for offline use).
- `launchers/` start scripts, self-updater, icons. `install/` one-line installers.
- `docs/vision/` the product vision and idea log. **AI agents: read `AGENTS.md` first.**
