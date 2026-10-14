# Tally - Product Vision

> **For AI coding agents (Claude Code, Codex, anything else):** read this file before
> changing anything. It is the owner's vision, written down so it never has to be
> re-explained. When the owner shares a new idea, add it to
> [`IDEAS_LOG.md`](IDEAS_LOG.md) (newest at the top) and, if it changes the vision,
> update this file too.

## The one-sentence version

**A beginner drops in any messy spreadsheet and gets back a clean, trustworthy,
easy-to-read story about what's in it, with charts they can present, without
learning any software.**

## Why it exists

Tools like Power BI are powerful, but you have to learn the software, clean data
by hand, and already know which variables are worth looking at. Tally is for the
person who has a random Excel file and *no idea where to even begin*. It makes
sense of the madness and hands them a deliverable they fully understand and can
present.

## Non-negotiables

1. **Accuracy above everything.** Analyse the *full* dataset, make no mistakes,
   never show a random pattern. Every finding must be backed by a real
   statistical test and be big enough to matter. If nothing real is found, say so
   honestly. (Implemented: deterministic stats in Python, Benjamini-Hochberg
   correction across all tests, effect-size floors, derived-column detection, a
   pure-noise regression test.)
2. **The AI never does the math.** The local LLM only rewords proven facts and
   suggests ideas. Any sentence containing a number that the statistics engine
   didn't produce is thrown away. Chat answers must come from tool calls on the
   real data.
3. **Simplicity is the name of the game.** No user should ever feel overwhelmed.
   Super-plain wording (explain like to a smart friend who is bad with tech).
   One idea per chart. Calm visuals.
4. **Looks modern and data/techy, but NOT "AI slop".** No purple gradients, no
   sparkle emojis, no glassmorphism overload, no walls of text. Clean, calm,
   comfortable to look at. Fun and satisfying to use.
5. **It tells a story.** Not necessarily chronological, but findings flow:
   big picture -> changes over time -> where it comes from -> what makes a
   difference -> what moves together -> worth a closer look -> what to do next.
6. **Descriptive -> prescriptive, gently.** Each finding says what the chart shows,
   what it means, and offers 1-2 humble, practical ideas ("You could...",
   "It might be worth..."). No bold claims. Always note correlation is not cause.
7. **Runs locally and privately.** AI runs on the user's computer via Ollama (no
   token costs, data never leaves the machine).
8. **Dead-easy install.** Double-click to start on Mac and Windows, with a cool
   logo. It pulls the latest version from GitHub on every start. A plain text
   guide explains Ollama setup step by step.

## What the app does (current scope)

- Upload CSV / Excel (multi-sheet) / TSV / JSON. Optional context box
  ("what is this data, what do you care about?").
- Auto-clean: finds the real header row under titles, drops Total/Subtotal rows,
  converts "$1,200" / "45%" / "(12)" into numbers, recognises dates, merges
  case-variant spellings, flags duplicates. Every fix is listed for the user.
- Finds and tests: trends over time, unusual spikes, day-of-week / seasonal
  rhythms, group differences, where totals come from (concentration), numbers
  that move together, categories that overlap, extreme outliers, and a "what
  drives the main metric" summary.
- Report = a story: title, intro, KPI tiles, "the short version" (3 takeaways),
  numbered chapters each with an interactive chart, plain explanation, ideas,
  a confidence label, "How do we know?" (the maths in plain words) and "See the
  numbers" (table view). Then next steps and an "About your data" section.
- "Ask Tally" chat about the data, answered by calculator tools on real rows.
- Save as PDF, PNG, or an interactive HTML file. Every report is auto-saved to
  **History** inside the app.
- Settings: connect Ollama, pick/download a model with a progress bar,
  turn AI wording on/off, light/dark theme.

## Brand

- **Name: Tally.** Counting/tallying data, friendly, short. The mascot is a little
  orange gumdrop character whose "hair" is a five-bar tally mark (four strokes
  plus a diagonal). Inspired by the Codex character icon: simple, cute, iconic.
- Mascot moods: idle (blinks), think (looks around while analysing, tally hair
  bounces), happy (hops when done), oops (errors).
- Palette: warm paper background, ink text, **Tally orange `#EB6834`** for
  personality, **one data blue `#2A78D6`** to highlight the point of each chart,
  quiet grey for everything else. System fonts, monospace for small "techy"
  labels. Full dark mode.

## Model guidance (Ollama)

**Default: `qwen3.5:9b`** (owner's choice). If it isn't downloaded, the app uses the
first installed model in this order: `gpt-oss:20b` (if 24 GB+ RAM) > `gemma4:e4b` >
`qwen3.5:4b` (low-memory machines). Owner originally suggested gpt-oss; it stays
supported and can be picked in Settings.

## Roadmap ideas (not built yet)

See [`IDEAS_LOG.md`](IDEAS_LOG.md) for the running list.
