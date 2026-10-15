# The Tally Data Storytelling Guide

**How to make charts and explanations that anyone understands at first glance, with almost no effort.**

This guide is the rulebook for everything Tally shows: the charts, the words, the numbers,
and the order they appear in. It is based on research in visual perception, cognitive
psychology, and data visualization (sources at the end). Tally's AI reads the
"Rules for the writer" section below **every time** it writes or re-reads an explanation.
People and coding agents changing Tally's charts or text should read the whole thing.

> **The one rule:** a person who has never seen the spreadsheet, and isn't comfortable with
> numbers or charts, should know what a chart is telling them **within about 5 seconds**,
> without having to work it out. If they have to think hard, we did it wrong, not them.

---

## 1. Know the reader

- **Assume low comfort with numbers.** In the 2023 international adult skills survey (PIAAC),
  about **34% of U.S. adults** scored at the lowest levels of numeracy, up from 29% in 2017.
  Many smart, capable people struggle with percentages, ratios and charts. Write for them.
- **Write at about an 8th grade reading level or lower.** This is the common plain-language
  benchmark used in government and healthcare writing.
- **Unfamiliar charts are hard.** Studies of people reading new kinds of charts find the
  biggest struggles are getting the gist and understanding how the chart works (what the
  colors, positions and shapes mean). People cope by connecting it to something familiar.
  So: use familiar chart types and say how to read them.
- **The reader didn't ask for the data, they asked for the answer.** Do the analysis for
  them. Never leave the reader to make the comparison themselves.

## 2. How eyes and brains read a chart (and what that means for us)

- **Some things "pop out" instantly.** Color, size, orientation and similar features are
  spotted in a single glance (about 200 milliseconds) without searching. Use **one** of these
  to point at the important thing. If everything pops out, nothing does.
- **Working memory is tiny: about 4 chunks.** People can hold roughly four things in mind at
  once. Every extra color, legend entry, number or line uses up that space.
  Keep each chart to **one message** and, ideally, **no more than about 4 things to keep track of**.
- **We see big patterns fast but compare details slowly.** The visual system is good at the
  overall shape ("going up") but slow and error-prone at comparing specific values or
  subsets. So **state the comparison in words** ("Sundays bring in about 1.9x more than
  Wednesdays"); don't make people do it with their eyes.
- **Some visual encodings are read more accurately than others.** From most to least
  accurate: position on a shared scale, then length, then angle and slope, then area, then
  color intensity. **Use position and length (bars, lines, dots) for the main comparison.**
  Avoid pies, bubbles and color-only encodings for anything the reader must compare.

## 3. Pick the simplest chart that shows the point

| The point is... | Use | Avoid |
|---|---|---|
| Change over time | **Line chart**, time left to right | Bars for long time series, area stacks |
| Which group is biggest / compare groups | **Horizontal bar chart, sorted biggest first** | Pie charts, unsorted bars |
| Share of a total | **Bar chart with the % written on each bar** | Pie or donut with many slices |
| Two numbers that move together | **Dot chart (scatter) with one trend line** | Two lines on two different y-axes |
| A single headline number | **The number itself, big** (a stat tile) | A chart with one bar |
| A few unusual values | **Bars for just those values, with a "typical" line** | A dense chart of everything |

- **Never use two y-axes on one chart.** The scales are arbitrary and invent patterns.
- **Never use 3D, shadows, or decoration that changes how big things look.**
- **Sort bars by size** (biggest at the top) unless the order means something (days, months).
- **Bars must start at zero.** Even when people are told the axis is cut off, a truncated
  axis still makes differences look bigger than they are.
- **Use few categories.** Show the top groups and fold the rest into "Other".

## 4. Color: one highlight, everything else quiet

- **Highlight one thing, gray the rest.** Research on "declutter and focus" found that
  highlighting the key data made charts look clearer and better designed **and** improved
  memory for the highlighted pattern. In Tally: the point of the story is **blue**, the rest
  is **gray**, and unusual values are **orange**.
- **Never rely on color alone.** About **8% of men** (and about 0.5% of women) have some form
  of color vision deficiency, mostly red-green. Always pair color with a label, position, or
  shape, and never use red vs green as the only difference.
- **Keep color meanings consistent across the whole report.** Blue always means "the one to
  look at", orange always means "unusual", gray always means "the rest".
- **Use meaningful colors when there's an obvious one.** Charts whose colors match the
  meaning of the categories (for example, the usual colors people associate with a
  category) are read faster. When there's no natural meaning, use the standard palette.
- **For "more vs less" on a scale, use one hue from light to dark.** Never a rainbow.
- **No more than about 7 distinct colors** carrying meaning in one view; fewer is better.
- **Always explain the colors** with a short key in words ("Blue bar: Downtown, the biggest")
  right next to the chart. Don't make people decode a legend.

## 5. Words: say the point, put it where the eye already is

- **The title states the takeaway, not the topic.** "Weekends bring in the most money", not
  "Revenue by day of week". In eye-tracking studies, titles were among the most-read parts of
  a chart, titles at the top were looked at more than titles at the bottom, and when the title
  stated the main message, people remembered the message.
- **Titles steer what people believe the chart says**, so they must be **accurate and
  neutral**. Studies show readers draw different conclusions from the same chart depending on
  the title's slant, and they often don't notice the slant. Never exaggerate in a title.
- **More helpful text on the chart is good.** In a study of 302 readers, people preferred
  charts with the **most** text annotations over charts with fewer annotations or text alone.
  Text that describes comparisons and relationships ("twice as high", "keeps rising") led
  readers to take away the comparison. Put the main message in the title and the specific
  notes **next to the data** they describe.
- **Put words right next to what they describe** (the "spatial contiguity" principle): label
  lines and bars directly instead of using a separate legend, and put the color key directly
  above the chart. Make the reader's eyes travel as little as possible.
- **Point the reader at the chart.** Tell them what to look at: "The blue bar is...",
  "Follow the dashed line...", "Each dot is one order...". This is "signaling", one of the
  best-supported ways to help people learn from graphics.
- **Remove anything that doesn't help** (the "coherence" principle): extra decoration,
  repeated words, background information that doesn't serve the one point.
- **Lead with the conclusion, then the proof, then what it means.** Readers stop early;
  make sure the first sentence alone is enough.
- **Interpret, don't just name.** Don't write "Revenue varies by Category". Write what it
  means in real life: "What people buy matters most for how much money an order brings in."
  Explain each column in everyday words the first time it appears.
- **Short sentences, one idea each.** Aim for under about 20 words. Use everyday words.
- **Banned words for the reader:** p-value, statistically significant, correlation,
  coefficient, variance, regression, median, distribution, quartile, standard deviation,
  dataset, variable, metric, insight. Say "typical" instead of "median", "move together"
  instead of "correlated", "very unlikely to be luck" instead of "significant".

## 6. Numbers: few, round, and compared to something

- **One or two key numbers per sentence. Never a wall of numbers.** Put exact values in the
  "See the numbers" table, not in the story.
- **Round hard.** $24,803.91 becomes $24.8K. 36.27% becomes 36%. Two or three significant
  digits is plenty. Always include the unit ($, %, orders, days).
- **Give every number something to compare against.** A number alone means little.
  "Downtown makes $24.8K" is weak; "Downtown makes 40% of all revenue, when an even split would
  be 25%" is clear. Short comparison sentences (ratios, ranks, "about the same as...")
  measurably improve how well people remember and understand numbers, and the effect lasted
  weeks.
- **Prefer "x times" and "out of" over complex percentages.** "About 2x as much" and "3 out of
  10 orders" are easier than "a 104% increase" or "0.3 probability". People understand
  counts ("natural frequencies") and pictures of counts better than percentages, and simple
  visuals help people stop ignoring the "out of how many" part.
- **Never show a relative change without the actual values.** "Up 50%" means nothing without
  "from $2,000 to $3,000".
- **Watch percent vs percentage points.** 20% to 25% is "5 percentage points", or "a quarter
  more", not "5% more".

## 7. Be honest about what the data can say

- **Only show patterns that passed the statistical checks.** If nothing passed, say so.
- **Moving together is not causing.** Always say so when showing two things that move
  together, and avoid cause-and-effect words (drives, causes, leads to) unless the data
  truly shows cause.
- **Say how sure we are in plain words** ("Very sure: this would happen by luck less than 1
  time in 1,000"), and keep the technical details one click away.
- **Never cut the bottom off a bar chart, never stretch an axis to exaggerate,** and keep
  the same scale when charts are compared.
- **Say what was left out or fixed** (cleaned rows, removed totals, partial months).

## 8. Layout and reading order

- **Same order every time** so people learn where to look: number and section label, then
  title (the takeaway), headline sentence (the proof), color key, chart, explanation (what it
  means), ideas (what to do), and how sure we are.
- **Top to bottom, most important first.** People read the top and left first and skim the
  rest.
- **Lots of white space, hairline grid lines, no borders around marks.** Decluttered charts
  are rated more professional and trustworthy.
- **One chart per idea.** If a chart needs two messages, make two charts.
- **Show the big picture first, details on demand.** The short version (3 takeaways) comes
  first; tables and the maths are behind "See the numbers" and "How do we know?".

## 9. Tell it as a story

- **Have a shape:** the big picture first, then how things changed, where it comes from,
  what makes a difference, what moves together, and what to look at more closely. End with
  what to do next.
- **Guide first, then let people explore.** The classic structure for data stories (the
  "martini glass") starts with a short author-guided story and then opens up for
  exploration. In Tally: the story and "Play the story" are the guided part; "See the
  numbers", chat, and the interactive charts are the exploring part.
- **Small, bite-sized steps.** One finding at a time, with a clear "next".
- **A little personality helps memory.** Friendly, relevant visual touches (like the mascot
  or a bold number reveal) can make charts more memorable later without hurting accuracy, as
  long as they never distort the data or crowd the chart.

## 10. The 5-second checklist (run it on every chapter)

Before showing any chart and explanation, check:

1. **Can someone say the main point after a 5-second look?** If not, fix the title.
2. **Does the title state the takeaway, accurately and without hype?**
3. **Is there exactly one highlighted thing,** and does the text name it by its color?
4. **Does the text tell the reader where to look** (which color, line, bar or dot)?
5. **Is every column explained in everyday words?**
6. **Is every number rounded, with a unit, and compared to something?**
7. **Are there no more than 1-2 numbers per sentence and about 4 things to track?**
8. **Are sentences short (under about 20 words) with no technical words?**
9. **Is anything claimed that the facts don't support** (cause, time periods, "most")?
10. **Would it still make sense in black and white** or to someone who is colorblind?

---

## Rules for the writer

The block below is loaded into Tally's AI instructions every time it writes or re-reads an
explanation. Keep it short, concrete and in plain words. Edit it here; the app picks it up
automatically.

<!-- TALLY-LLM-RULES:START -->
The reader has never seen this spreadsheet and is not comfortable with numbers or charts.
They must understand each chapter within about 5 seconds, with almost no effort.
1. Lead with the conclusion in plain words, then give the one number that proves it.
2. The title says what is true (e.g. "Weekends bring in the most money"), never just the topic. Keep it accurate and calm, no hype.
3. Tell the reader exactly where to look, using the chart's colors and shapes from the chart key ("The blue bar is Downtown, the biggest").
4. Interpret, don't just name columns. Say what each column means in real life the first time you use it ("Revenue" = "the money each order brought in").
5. Use at most 1 or 2 numbers per sentence. Copy numbers exactly as given (they are already rounded) and always keep their units.
6. Give every number something to compare against: "about 2x Wednesday", "40%, when an even split would be 25%". Prefer "x times" and "out of" over complicated percentages.
7. Short sentences (under 20 words), one idea each, everyday words a 12-year-old knows, active voice.
8. Never use: p-value, statistically significant, correlation, coefficient, variance, regression, median, distribution, quartile, standard deviation, dataset, variable, metric, insight. Say "typical" for median and "move together" for correlated.
9. Moving together is not causing. Never use cause words (drives, causes, leads to, because of) unless the facts say so.
10. Only use the facts given. Never invent, estimate or calculate a number, a cause, a time period, or a link to another column.
11. Keep one message per chapter. Leave details for the table; don't list many values.
12. Ideas are gentle and practical ("You could...", "It might be worth..."), tied to this data.
13. Never use the em dash character. No emojis. No hype words (amazing, game-changer, unlock, delve, leverage).
<!-- TALLY-LLM-RULES:END -->

---

## How Tally applies this guide (for developers and coding agents)

| Guide rule | Where it lives |
|---|---|
| Only proven patterns, honest about luck | `tally/insights.py` (tests, Benjamini-Hochberg correction, effect-size floors) |
| AI can't change numbers | `tally/narrate.py` `numbers_ok()` |
| Rules for the writer loaded every time | `tally/narrate.py` loads the block above into the AI's instructions |
| 5-second re-read of every chapter | `tally/narrate.py` `review_insight()` plus `readability_flags()` |
| One highlight color, gray rest, orange unusual, color keys | `tally/insights.py` chart `key`s, `tally/static/js/charts.js` |
| Sorted horizontal bars, zero baselines, no dual axes, direct value labels | `tally/static/js/charts.js` |
| Rounded numbers with units | `tally/fmt.py`, `tally/static/js/format.js` |
| Same reading order on every chapter, details on demand | `tally/static/js/report-view.js` |
| Guided story first, exploration after | report layout, "Play the story" (`story.js`), "See the numbers", chat |

When adding a new kind of finding or chart, make sure it passes the 5-second checklist and
has a color key.

---

## Sources

- Franconeri, Padilla, Shah, Zacks & Hullman (2021). *The Science of Visual Data Communication: What Works.* Psychological Science in the Public Interest. https://doi.org/10.1177/15291006211051956
- Cleveland & McGill (1984). Graphical perception ranking (position, length, angle, area, color); replicated by Heer & Bostock (2010). Summary: https://flowingdata.com/2010/03/20/graphical-perception-learn-the-fundamentals-first
- Borkin et al. (2015). *Beyond Memorability: Visualization Recognition and Recall.* IEEE TVCG. https://vcg.seas.harvard.edu/publications/20150101-beyond-memorability-visualization-recognition-and-recall
- Kong, Liu & Karahalios (2018). *Frames and Slants in Titles of Visualizations on Controversial Topics.* CHI. https://mail.zcliu.cs.umd.edu/vistitles/CHI18-VisTitles.pdf
- Stokes, Setlur, Cogley, Satyanarayan & Hearst (2022). *Striking a Balance: Reader Takeaways and Preferences when Integrating Text and Charts.* IEEE VIS. https://content.ieeevis.org/year/2022/paper_v-full-1024.html
- Ajani, Lee, Xiong, Knaflic, Kemper & Franconeri (2021). *Declutter and Focus: Empirically Evaluating Design Guidelines for Effective Data Communication.* IEEE TVCG. https://visualthinking.psych.northwestern.edu/projects/DeclutterFocus
- Correll, Bertini & Franconeri (2020). *Truncating the Y-Axis: Threat or Menace?* CHI. https://arxiv.org/pdf/1907.02035
- Barrio, Goldstein & Hofman (2016). *Improving Comprehension of Numbers in the News.* CHI. https://microsoft.com/en-us/research/?p=215388 ; Riederer, Hofman & Goldstein (2018), effects lasting six weeks.
- Garcia-Retamero, Galesic & Gigerenzer (2010). Icon arrays reduce denominator neglect. https://ideas.repec.org/a/sae/medema/v30y2010i6p672-684.html
- Lin, Fortuna, Kulkarni, Stone & Heer (2013). *Selecting Semantically-Resonant Colors for Data Visualization.* https://idl.uw.edu/papers/semantically-resonant-colors
- Healey, Booth & Enns (1993) and Healey's work on preattentive processing. https://healey.csc.ncsu.edu/publications/15885-harnessing-preattentive-processes-for-multivariate-data-visualization
- Cowan (2001). *The magical number 4 in short-term memory.* Behavioral and Brain Sciences. https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/article/magical-number-4-in-shortterm-memory-a-reconsideration-of-mental-storage-capacity/44023F1147D4A1D44BDC0AD226838496
- Mayer, multimedia learning principles (coherence, signaling, spatial contiguity). https://resolve-he.cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/principles-for-reducing-extraneous-processing-in-multimedia-learning-coherence-signaling-redundancy-spatial-contiguity-and-temporal-contiguity-principles/CD5B7AE1279A9AB81F8EEBB53DBEC86E
- Segel & Heer (2010). *Narrative Visualization: Telling Stories with Data.* IEEE TVCG. https://homes.cs.washington.edu/~jheer/files/narrative.pdf
- Bateman et al. (2010). *Useful Junk? The Effects of Visual Embellishment on Comprehension and Memorability of Charts.* https://vis.csail.mit.edu/classes/6.859/readings/pdfs/Bateman-UsefulJunk.pdf
- Skau & Kosara (2016). *Arcs, Angles, or Areas: Individual Data Encodings in Pie and Donut Charts.* https://tableau.com/sites/default/files/2023-01/Skau-EuroVis-2016.pdf
- Rezaie et al. (2024). *Struggles and Strategies in Understanding Information Visualizations.* https://vis.khoury.northeastern.edu/pubs/Rezaie2024StrugglesStrategiesUnderstanding
- U.S. PIAAC 2023 results (adult literacy and numeracy). https://ies.ed.gov/learn/press-release/u-s-adults-score-par-international-average-literacy-skills-below-international-average-numeracy-and
- Color vision deficiency and colorblind-safe palettes: Jenny & Kelso (2007), *Cartographic Perspectives*. https://cartographicperspectives.org/index.php/journal/article/download/cp58-jenny-kelso/pdf/1569
- Plain-language reading level benchmarks (8th grade). https://hub.innovation.ca.gov/content-design/principles/write-in-plain-language/
