---
name: PARAKH
description: Is this prompt or model change safe to ship?
colors:
  bg: "#14100c"
  panel: "#1c1611"
  panel-2: "#241c16"
  panel-3: "#2d241c"
  border: "#382d23"
  control-border: "#806d57"
  text: "#f4ede3"
  text-2: "#dbcfbf"
  muted: "#ab9a83"
  amber: "#e7a84f"
  amber-ink: "#1b1107"
  focus: "#f6c77e"
  primary: "#f4ede3"
  primary-ink: "#17110c"
  pass: "#93cf86"
  pass-bg: "#1d2a1a"
  pass-line: "#3f6b38"
  fail: "#ff7a66"
  fail-bg: "#3a1813"
  fail-line: "#8a3a2e"
  warn: "#f2b54e"
  warn-bg: "#36260f"
  warn-line: "#7a5a22"
  unv: "#a9b8cf"
  unv-bg: "#1f232c"
  unv-line: "#5d6a80"
  info: "#c3adec"
  info-bg: "#2a2238"
  series-score: "#e7a84f"
  series-pass: "#7fb6dd"
typography:
  display:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(40px, 5.2vw, 68px)"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(32px, 4.4vw, 54px)"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    letterSpacing: "-0.01em"
  measure:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  body:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "ss01"
  label:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 500
  tag:
    fontFamily: "Geist, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    letterSpacing: "0.02em"
  mono:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, monospace"
    fontSize: "12.5px"
    fontWeight: 400
  deva:
    fontFamily: "Tiro Devanagari Hindi, serif"
    fontSize: "clamp(24px, 2.6vw, 34px)"
    lineHeight: 1
rounded:
  tag: "5px"
  ctl: "7px"
  r: "10px"
  hero: "14px"
  pill: "999px"
spacing:
  gutter: "clamp(16px, 3vw, 40px)"
  xs: "6px"
  sm: "12px"
  md: "20px"
  lg: "28px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-ink}"
    rounded: "{rounded.ctl}"
    padding: "8px 22px"
    height: "40px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.ctl}"
    padding: "8px 16px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.panel-2}"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.fail}"
    rounded: "{rounded.ctl}"
  button-danger-hover:
    backgroundColor: "{colors.fail-bg}"
  select:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.text}"
    rounded: "{rounded.ctl}"
    padding: "8px 34px 8px 12px"
    height: "40px"
  tag-pass:
    backgroundColor: "{colors.pass-bg}"
    textColor: "{colors.pass}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "2px 8px"
  tag-fail:
    backgroundColor: "{colors.fail-bg}"
    textColor: "{colors.fail}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "2px 8px"
  tag-warn:
    backgroundColor: "{colors.warn-bg}"
    textColor: "{colors.warn}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "2px 8px"
  tag-unverified:
    backgroundColor: "{colors.unv-bg}"
    textColor: "{colors.unv}"
    typography: "{typography.tag}"
    rounded: "{rounded.tag}"
    padding: "2px 8px"
  panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.r}"
    padding: "12px 20px"
  verdict-card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.hero}"
    padding: "clamp(18px, 2.4vw, 32px)"
  verdict-stamp:
    size: "96px"
    rounded: "{rounded.pill}"
  case-cell:
    rounded: "{rounded.ctl}"
    padding: "8px 2px 6px"
    height: "64px"
  gauge:
    backgroundColor: "{colors.panel-3}"
    height: "6px"
---

# Design System: PARAKH

## Overview

**Creative North Star: "The Tasting Bench"**

A release check read as a tea-tasting: every case is graded baseline against candidate on one bench, and the verdict lands as a stamped grade. The ground is brewed-leaf dark, panels steep one step lighter, text is porcelain, and amber is the assayer's mark. Verdict colours sit on top of that world and never replace it.

Density is operational, not decorative. Structure comes from hairline rules and tonal steps, not boxes inside boxes: only the run bar, the status block and the verdict hero are framed panels; everything else (results, history, rail sections, metrics) is divided by 1px rules on the ground.

**Key Characteristics:**
- Warm near-black ground with three tonal panel steps; no grey.
- One brand accent (amber), four state colours (pass, fail, warn, unverified) each with a text, fill and line tone.
- Every state carries a word or a mark shape, never colour alone; unverified is always dashed.
- Geist for interface, Geist Mono for ids, numbers, deltas and logs, Tiro Devanagari only for परख.
- Small radii, hairlines, one soft ambient shadow under the verdict hero; no glow.

## Colors

Steeped browns and porcelain carry the page; amber marks the brand; the verdict palette is reserved for meaning.

### Primary
- **Assay Amber** (amber): the cupping-bowl mark, परख, MongoDB machinery icons, the selected run's timeline node, checkbox accent, progress bar, links. Text on amber uses Amber Ink (amber-ink).
- **Porcelain** (primary / primary-ink): the primary button is a porcelain slab with dark ink; hover goes to pure white.

### Neutral
- **Brewed Leaf** (bg): page ground, and the inset ground for raw output blocks.
- **Steeped Panel 1/2/3** (panel, panel-2, panel-3): framed panels and row hover; control fills and selected rows; neutral tags, gauge tracks and tooltips.
- **Hairline** (border): every structural rule and panel edge.
- **Control Edge** (control-border): edges of buttons, selects, chips and the empty-verdict ring; held at 3:1 or better on panel and panel-2.
- **Porcelain Text / Tea Text / Muted Leaf** (text, text-2, muted): primary copy; secondary copy and ids; labels, captions, meta.
- **Focus Gold** (focus): the only focus ring colour.

### Verdict and case states
- **Leaf Green** (pass, pass-bg, pass-line): SAFE, passed, fixed, better-than-baseline deltas, inserted diff words.
- **Fired Red** (fail, fail-bg, fail-line): NOT SAFE, failed, regressed, lost cases, deleted diff words, danger buttons, error toast.
- **Warning Amber** (warn, warn-bg, warn-line): RISKY, still failing, limit breaches, the mock-data notice.
- **Unverified Slate** (unv, unv-bg, unv-line): INCONCLUSIVE, timeout, error, simulated-timeout chips.
- **Running Violet** (info, info-bg): in-flight state and pending notes only.
- **Chart series** (series-score, series-pass): amber vs porcelain blue, separable for colour-blind readers.

**The Three-Tone State Rule.** Every state is a triple: bright text, dark fill, mid line. Tags and case cells use all three; inline text uses the bright tone alone.

**The Slate Is Not Grey Rule.** Unverified has its own cool slate hue and a dashed border everywhere it appears (tag, cell, mark, gauge, stamp). It must never be confusable with pass, fail or the warm neutrals.

## Typography

**Display Font:** Geist (with ui-sans-serif, system-ui)
**Body Font:** Geist, stylistic set ss01
**Label/Mono Font:** Geist Mono (with ui-monospace, SFMono-Regular)
**Script:** Tiro Devanagari Hindi, for परख only

**Character:** a precise grotesk with tight negative tracking at size, paired with a mono that does all the counting.

### Hierarchy
- **Display** (700, clamp 40–68px, 0.95, -0.035em): the PARAKH wordmark only.
- **Headline** (700, clamp 32–54px, 1, -0.03em): the verdict title, in the verdict colour, written in capitals (SAFE TO SHIP, RISKY, NOT SAFE TO SHIP, INCONCLUSIVE).
- **Title** (600, 18px; 15px in the rail; 16px for sub-heads): section headings, sentence case.
- **Measure** (600, 22px, tabular figures): baseline → candidate values in the metrics strip.
- **Body** (400, 15px, 1.55): reasons and copy; verdict sub-line at 16px, max 62ch. Secondary text at 13–13.5px.
- **Label** (500, 12.5px): field labels, table heads, meta; muted colour, sentence case.
- **Tag** (600, 12px, +0.02em): state tags.
- **Mono** (400–500, 12–13px): case ids, run ids, deltas, gauge keys, latency and cost cells, logs, raw output.

**The Mono Counts Rule.** Anything that is an identifier, a number to compare, or machine output is Geist Mono or tabular figures. Prose is never mono.

## Layout

Max width 1480px, side gutter clamp(16px, 3vw, 40px). Order: masthead (wordmark left, status block right), a slim full-width run bar, then a two-column main of fluid content plus a 360px rail (gap 28px / 40px). Below 1080px the rail stacks under the content; below 760px the masthead, run bar, metrics strip and diff columns go single-column.

The tasting line is a 15-column grid of the 30 cases (10 columns under 900px, 5 under 560px), held between two hairlines. The metrics strip is three equal columns split by vertical hairlines. Section rhythm is 28px between sections, 20–22px inside them, 6–14px within groups.

## Elevation & Depth

Depth is tonal: ground, then panel steps. Hairlines do the separating. Two shadows exist, both soft and ambient, never coloured.

### Shadow Vocabulary
- **Hero lift** (`box-shadow: 0 18px 50px -24px rgba(0,0,0,.7)`): the verdict card only.
- **Float** (`box-shadow: 0 12px 30px -8px rgba(0,0,0,.6)`): chart tooltip and error toast, things that sit above the page.

**The Flat Bench Rule.** Sections, rail cards, tables and cells sit flat on the ground. Only the verdict hero and floating layers get a shadow.

## Shapes

Small, consistent radii: 5px tags and chips, 7px controls, cells, rows and code blocks, 10px panels, 14px the verdict hero, full round for dots, marks, status pills and the stamp. Borders are 1px hairlines; dashed borders mean unverified and nothing else. Reason bullets are small rotated squares in the verdict colour.

## Components

### Buttons
- **Shape:** gently squared (7px), min height 40px; small 32px.
- **Primary:** porcelain fill, dark ink, 600 weight, 8px 22px. Hover to white. At most one per area (Run, Compare).
- **Secondary:** transparent with Control Edge; hover lifts to panel-2 with a text-2 edge. Active nudges 1px down.
- **Danger:** fail-line edge and fail text; hover fills fail-bg.
- **Disabled:** 45% opacity.

### Chips
- **Style:** mono case ids, 5px radius, Control Edge, 30px min height.
- **State:** selected chips turn slate (unv-bg, unv border) with a small dashed ring, because a simulated timeout is an unverified case.

### Tags
- Word-first state labels: pass/fixed green, fail/regressed red, still failing/warn amber, timeout/error/unverified slate and dashed, running violet, still passing neutral on panel-3.

### Cards / Containers
- **Corner Style:** 10px (panels), 14px (verdict hero).
- **Background:** panel on bg, hairline border.
- **Internal Padding:** 12px 20px for the run bar, 14px 18px for the status block, clamp(18px, 2.4vw, 32px) for the hero.
- Most sections are not cards: a top hairline and 22–26px padding.

### Inputs / Fields
- **Select:** panel-2 fill, Control Edge, 7px, 40px, custom muted chevron; hover edge to text-2.
- **Focus:** 2px Focus Gold outline at 2px offset on every focusable element.

### Navigation
- Run history is a timeline: a hairline spine, 7px hollow nodes, the selected run filled amber with its row on panel-2.

### Verdict Stamp (signature)
A 96px circle (76px on narrow screens) in the verdict fill with a 2px verdict-colour ring and a second 1px ring at 4px offset, rotated -8deg, holding a stroked SVG icon. Dashed when INCONCLUSIVE. On a fresh verdict it stamps in (scale 1.35 → 0.96 → 1, 0.45s, ease cubic-bezier(.16,1,.3,1)) and the title and sub-line rise 6px. Stale verdicts drop to 40% and greyscale.

### Tasting Line (signature)
Each of the 30 cells shows the mono case id over two 10px marks, baseline → candidate: filled = passed, hollow = failed, dashed = unverified. Regressed, fixed and unverified cells take their three-tone state; still failing takes only the warn line. Hovering or selecting a cell dims the rest to 45%; the selected cell gets a 2px text outline and lifts 3px at scale 1.06.

### Delta Gauge (signature)
A 6px panel-3 track with the candidate bar (text-2 by default; warn on breach, fail on loss, pass when better, dashed slate when unverified) and a 2px porcelain tick for the baseline or limit. A mono key sits underneath.

### Event Log
Mono 12.5px lines on a darker inset well, newest line flashing in from panel-3; colours follow the state palette.

## Do's and Don'ts

### Do:
- **Do** pair every state colour with a word, a mark shape (filled, hollow, dashed) or an icon.
- **Do** use hairline (border) rules to separate sections; reserve framed panels for the run bar, status block and verdict.
- **Do** keep amber for brand and selection; use warn for warnings even though the hues are close.
- **Do** draw icons as stroked inline SVG (1.5–1.6px, round caps, currentColor).
- **Do** honour reduced motion: keep every state change, drop movement (stamp, lift, rise, transitions).
- **Do** label mock-derived numbers as illustrative, with the warn triangle.

### Don't:
- **Don't** present INCONCLUSIVE or unverified in green, or with a solid border.
- **Don't** put grey neutrals or cool backgrounds into the ground; neutrals are warm browns.
- **Don't** add glows or coloured shadows; depth is tonal plus the two ambient shadows.
- **Don't** set prose, headings or labels in mono, or in uppercase; capitals belong to the four verdict names (the stamped grade) and nothing else.
- **Don't** use Tiro Devanagari for anything but परख.
