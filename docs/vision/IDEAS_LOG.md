# Ideas log

A running, dated log of the owner's ideas and decisions. **Newest at the top.**
Agents: append here whenever the owner shares a new idea, preference, or decision,
even small ones. Mark items `[built]`, `[planned]`, or `[idea]`.

---

## 2026-10-14 - Original brief (first build)

The owner's original request, captured in full so no context is lost:

- [built] An "AI data analysis agent" app that runs on the computer, with a
  cute/modern/clever name and a cute icon, inspired by the Codex character icon.
  -> Named **Tally**, orange gumdrop mascot with tally-mark hair.
- [built] User uploads a CSV / Excel workbook / similar. The app analyses the
  *full* spreadsheet, **making no mistakes**.
- [built] It decides which graphs / interactive visualisations are worth showing,
  only where it genuinely found a meaningful pattern **backed by statistical
  analysis**. "It is so important that it is accurate and not random."
- [built] Each chart comes with SUPER easy, plain-language interpretation, plus
  some meaningful action ideas (prescriptive), "nothing too bold".
- [built] All analyses and charts must be simple, easy and comfortable to look at.
  The user should never feel overwhelmed.
- [built] The data should "tell a story" (not necessarily chronological).
- [built] A complex dataset should give meaningful information that even someone
  "horrible with technology" can fully understand. Simplicity is key. Fun, clean,
  satisfying experience.
- [built] Frontend to input data, plus an optional chatbot / context box (not
  required).
- [built] AI runs locally with Ollama (avoid hosted token costs). Owner suggested
  gpt-oss; asked for suggestions of other free models that might be better.
- [built] Results go back to the frontend as graphs, interpretations, and
  interactive elements.
- [built] Save button: PDF, PNG, and an interactive file. Plus a **History** tab
  in the app to revisit past interactive reports.
- [built] Why: Power BI is powerful but you must learn it, clean data by hand, and
  know which variables matter. A beginner should be able to upload a random Excel
  file with no idea where to begin, and get a deliverable they understand and can
  present.
- [built] Visuals are very important: modern, data/techy, but **NOT AI slop**.
  Not overwhelming, not a headache. Simplicity is the name of the game.
- [built] As easy to install as possible: a double-click button for Mac and
  Windows (with a cool logo) that pulls the latest version from GitHub and then
  opens the app.
- [built] A simple text document explaining, in very easy steps, how to set up
  Ollama and connect it to the app. (Owner didn't know how to do this either.)
- [built] Keep a log/folder of the owner's visions so both Claude Code and Codex
  know them without re-prompting. -> This folder, plus `AGENTS.md` and `CLAUDE.md`.

### Ideas for later (suggested during the first build, not yet requested)
- [idea] Let the user pick the "main metric" from a dropdown after the report
  is made, and re-run the story around it.
- [idea] Compare two files (this month vs last month) and tell the story of what changed.
- [idea] Forecast the next few periods for a clear trend, with an honest range.
- [idea] A "presentation mode" that turns the chapters into full-screen slides.
- [idea] Package as a real signed desktop app (Tauri/Electron) once the design settles.
- [idea] PowerPoint export.
