# 1–3. Define, design and plan: map error fix, news sections as dropdowns, and how a walk is scored

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Approved
**Adds to and revises:** [01-03-news.md](01-03-news.md) (section layout). Item 3 revises the route score in [01-definition.md](01-definition.md) ("an overall score from 0 to 100, which is the highest score along the route (one risky stretch is never averaged away)"; criterion 13). This document covers phases 1–3 in one, as the workflow allows for a small addition.

## What this step is
This document agrees three changes Sai asked for after using the site. One approval covers the definition, design and plan.

## What was done
On 2026-10-15 Sai sent a screenshot of a walk, Union → Kensington Market, scored "75 High risk", with the red message "routeLayer.bringToFront is not a function" above the panel. Sai wrote:

> the news and patterns part is a cluttery can we make those dropdowns with each section as its own … routeLayer.bringToFront is not a function got this displayed on the screen for somereason … also union to kensingotn is highrisk al day seems a little agressivve

### 1. The error message: a bug since the first version
- **Where:** `app.js`, `loadCells()`, calls `routeLayer.bringToFront()` after drawing street blocks, so the walk stays on top. But the walk is drawn into an `L.layerGroup`, which has no `bringToFront` (only `L.featureGroup` does).
- **When it happens:** after a walk is shown, any zoom or pan at street level throws, and the error appears as the status message. The street blocks for that view are still drawn, but the walk ends up underneath them.
- **Since when:** the line was in the first web map commit (`c1f698f`, 2026-10-01).
- **Why the checks missed it:** they never moved the map after a walk.

### 2. "News and patterns" is cluttered
- **What the section holds:** Trending (up to 3 groups), then three lists (protests, violent incidents and property crime, 5 shown each), then the patterns.
- **How long it gets:** about 2.5 screens on a laptop today. Below the score panel it pushes "Data collected" far down.

### 3. The walk score
- **How it works:** a walk's headline score is its worst block, by the approved definition. The worst block's categories and reasons are what the panel shows.
- **Union → Kensington:**
  - **The record:** 95 on 2026-10-01, 87 after the fairness recalibration ([04-implementation.calibration-crowds-heat.md](04-implementation.calibration-crowds-heat.md)), 75 today. The worst block is near Kensington ("125 assaults within about 250 m… about 5.6× the reported street crime per person of a typical Toronto block").
  - **The rest of the walk:** the panel also says "mostly moderate risk (30)": `typical_score`, the median block, weighted by how much of the walk is in each block.
- **What a reader sees:** "High risk" in large type, even though most of the walk is moderate. That's what Sai calls aggressive.
- **The tension:** the original rule exists so "one risky stretch is never averaged away". Any change should keep the risky stretch visible.

## Definition

### In scope
1. **Fix the error.** The walk is drawn in a layer that supports `bringToFront`. Moving the map after a walk shows no error, and the walk stays on top of the street blocks.
2. **"News and patterns" as five dropdowns,** each its own section, closed by default. Each heading shows its count, so you can see what's inside without opening it:
   - "Trending (2)"
   - "Protests · last 2 days (4)"
   - "Violent incidents · last 7 days (6)"
   - "Property crime · last 60 days (12)"
   - "Patterns in police reports (6)"

   Opening one shows its full list, so "Show all" is no longer needed. The "unverified" tags and the note under the patterns stay inside their sections.
3. **The walk's headline score is the typical block,** and the worst stretch stays visible:
   - **Gauge and band:** they show the typical score ("Moderate risk 30").
   - **The worst block** gets its own small marker on the same dial (a red-outlined triangle on the arc at 75), and a line right under the title: "Worst block: 75 (high risk) · highlighted on the map". It's also still drawn as the thick stretch on the map.
   - **Category bars and reasons:** they describe the typical block. A short "Worst block" list keeps that block's own reasons, so nothing about it is hidden.
   - **Official alerts and news anywhere on the walk** still show, because they're among the worst block's reasons whenever they make it the worst.

### Out of scope
- **Places:** neighbourhood and street-block scores are unchanged; this is walks only.
- **The API's existing `score` field for a walk** stays the worst block, for compatibility. A new `typical` object is added (see the design).

### Acceptance criteria (added to criteria 1–51)
52. **No error after moving the map.** In the browser check: show a walk, then zoom and pan three times at street level. No status error, no console error, and the walk line is still above the street blocks (drawn later in the map's layer order).
53. **Five dropdowns.** "News and patterns" has 5 sections, all closed on load, with headings showing type, window and count as above. Opening one shows all its items; closing hides them. No "Show all" buttons remain. No sideways scrolling at phone width.
54. **Typical score on the gauge for a walk.**
    - **API:** `/route-risks` returns `typical` (the median block's `score`, `band`, `categories` and `reasons`); `score` and the existing fields are unchanged. A unit test checks that `typical` is the length-weighted median block.
    - **Panel:** the gauge shows the typical score, and the worst block is a separate marker at its own score, with the line "Worst block: N (band) · highlighted on the map".
    - **Live check:** Union → Kensington shows about 30 (moderate) on the gauge and 75 as the worst block.
55. **Nothing lost about the worst block.** Its reasons are listed under "Worst block". A walk passing through an area under an official warning still shows the warning (via the worst block). Test: the seed data's warning square (Test Warning, alert score 90).

## Design
- **Item 1:** `routeLayer = L.featureGroup().addTo(map)`, one line. The browser check gets the move-after-walk steps.
- **Item 2:** `index.html` replaces the section's three headings with five `<details>` elements. `loadNews()` fills each `<summary>` with "Name · window (count)" and each body with its list. The `newsGroup()` "Show all" logic is removed.
- **Item 3:**
  - **API (added fields only):** in `route_risks.py`, find the median block itself, not just its score: `route_rules.typical_cell(points, scores)` returns the cell. Then `typical: scored[cell].to_dict()`, and `typical_score` and `typical_band` come from it, as now.
  - **Page:** `runRoute()` passes `d.typical` to `showScore()` for the gauge, bars and reasons, and passes the worst block as `worst`.
  - **Gauge:** `setGauge(score, band, worst)` draws a small triangle marker on the arc at the worst score, coloured by its band, with a dark outline so it reads on any colour. The marker is hidden when there's no `worst` (places) or when the worst equals the typical. The `aria-label` gains ", worst block 75: high risk".
  - **Worst block list:** a short "Worst block" heading with its reasons, before "Stretches that stand out".
- **The rules page** "Walking routes" text: "A walk's score is its typical block (the median, weighted by distance); the worst block is marked on the dial and highlighted on the map."

### Review checklist

| Area | Finding |
|---|---|
| Correctness | **The typical block** is already computed by the approved `typical_score` logic; only the cell is now returned as well. **The worst block's data** is unchanged in the API. |
| Safety messaging | **The worst stretch is never hidden:** marker, line, map highlight and its own reasons. **Alerts** still show through the worst block. **The rule is still "higher = riskier".** |
| Compatibility | **`/route-risks`:** fields added only. Existing clients reading `score` still get the worst block. |
| Accessibility | **Native `<details>`/`<summary>`** are keyboard- and screen-reader-friendly. **The worst-block marker** is also in words and in the gauge label. |

### Alternatives considered (item 3)
1. **Keep the worst block as the headline** (today). It's the safest reading of a route, but it makes most downtown walks "high", which is what Sai finds aggressive.
2. **The 90th percentile by distance:** for this walk the 833 m stretch near Kensington is about 30% of the route, so it would still read about 75. It doesn't address the concern.
3. **The typical block, with the worst marked (recommended).** It answers "what's this walk like?" and still flags the worst part.

## Plan
Branch `feature/panel-tidy` from `main`.

| # | What | Files | Tests | Done when |
|---|---|---|---|---|
| T1 | Bug fix and regression check (TDD: the browser check fails first) | `web/app.js` | Criterion 52 | Fails before, passes after |
| T2 | News dropdowns | `web/index.html`, `web/app.js`, `web/style.css` | Criterion 53 | Pass |
| T3 | Walk: `typical_cell`, `typical` in the API, gauge marker, "Worst block" line and list, rules page | `scoring/route.py`, `api/routes/route_risks.py`, `web/app.js`, `web/style.css`, `web/rules.html` | Criteria 54–55 (unit, API and browser) | Pass |
| T4 | Acceptance check, E2E rows 6, 30 and 54; build and test records; after your approval, merge, deploy and production check | `scripts/acceptance_check.py`, `06-e2e-signoff.md` | Full suite; production | Pass |

## Decision for you
**Item 3, the walk's headline score:**
- **(a) recommended:** the typical block on the gauge, with the worst block marked on the dial, in a line under the title, and on the map
- **(b)** keep the worst block as the headline, and only make the "mostly moderate (30)" line more prominent

## Approval
- **Status:** Approved (option (a) for item 3)
- **Approved by:** Sai Kaja
- **Date:** 2026-10-15 15:46
- **User's response:** "aprove a"
- **Revisions before approval:** none
