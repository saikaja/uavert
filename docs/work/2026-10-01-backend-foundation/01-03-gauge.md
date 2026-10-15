# 1–3. Define, design and plan: the risk score as a speedometer gauge

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Adds to:** the details panel from [01-definition.md](01-definition.md) and [01-03-odds-percent.md](01-03-odds-percent.md) (the "Risk score" label). This document covers phases 1–3 in one, as the workflow allows for a small addition.

## What this step is
This document agrees how the score badge becomes a gauge. One approval covers the definition, design and plan.

## What was done
- **The request.** Sai asked, on 2026-10-15: "i now want Odds score showing as a sort of speedometer needle with color coding that matches the maps".
- **Which number.** Asked which number the gauge shows. Sai chose "Risk score": the 0–100 score, replacing the square badge, for neighbourhoods, street blocks and walks. The odds table stays as it is.
- **The current panel:**
  - **The badge:** a 64 × 64 px square, `#score-badge`, filled with the band colour and showing the number.
  - **Next to it:** "Risk score (0–100, higher = riskier)", the band name, the place and the "Showing: …" line.
  - **Colours:** they come from `BANDS` in `app.js`, the same constant the map uses, so the gauge can't drift from the map.
  - **Tests:** the browser checks and E2E rows read the number from `#score-badge`.

## Definition

### Goal
The score reads at a glance like a speedometer, with the dial coloured exactly like the map.

### In scope
- **The gauge:** a half-circle dial from 0 (left) to 100 (right), in four coloured sections that match the map bands:

  | Section | Scores | Colour |
  |---|---|---|
  | Lower reported risk | 0–24 | green |
  | Moderate risk | 25–49 | yellow |
  | Elevated risk | 50–74 | orange |
  | High risk | 75–100 | red |

  A needle points at the score, and the number sits under the needle's hub.
- **Where it's used:** wherever the badge was: neighbourhoods, clicked street blocks and walks. The label, band name and place stay to its right as now.
- **Small marks** at 0, 25, 50, 75 and 100.
- **Movement:** the needle moves smoothly to a new score (about 0.4 s) when the score changes, for example on a time change. It doesn't move for people who have asked their system for reduced motion.

### Out of scope
- **Odds and trends:** unchanged.
- **Map colours and bands:** unchanged.
- **Other gauges:** none per category; the category bars stay.

### Acceptance criteria (added to criteria 1–47)
48. **Gauge for every kind of result.** A neighbourhood, a street block and a walk each show the gauge. Its four sections use exactly the `BANDS` colours, read from the page in the browser check. The needle's angle is `score / 100 × 180°`, checked for scores 0, 25, 63 and 100.
49. **The number is still readable as text.** It's in `#score-badge`, so existing checks keep working. The gauge has `role="img"` and a label such as "Risk score 63 out of 100: elevated risk".
50. **Fits and reads in both themes.** No sideways scrolling at phone width (390 px). The needle and number are readable in light and dark mode. Screenshots of each band.
51. **No console errors**, and the full browser check from earlier additions still passes.

## Design
- **Markup:** `#score-badge` becomes a container for an inline SVG, 132 × 76 px, drawn by `gaugeSvg(score, band)` in `app.js`:
  - **Sections:** four arcs, one per band, from the band limits in `BANDS`.
  - **Arc maths:** for a score s, the angle is 180° − s/100 × 180° (0 = left, 100 = right). An arc point is (cx + r·cos θ, cy − r·sin θ).
  - **Needle:** a line from the hub, in the text colour, turned with a CSS transform (`rotate`), so it can animate.
  - **Number:** large text under the hub; the band name stays next to the gauge as today.
- **Building it:** the SVG is created with `createElementNS`, like the trend chart, never from HTML strings.
- **Band edges:** `bandFor`'s thresholds (25, 50, 75) and the `BANDS` colours are reused, so there's a single source for each.
- **CSS:**
  - remove the square badge's fill
  - `.gauge .needle { transition: transform .4s ease-out }`
  - `@media (prefers-reduced-motion: reduce) { transition: none }`
- **Accessibility:** the gauge itself is decorative inside a labelled `role="img"` wrapper. The visible band name next to it still says the level in words, so colour isn't the only signal.

### Review checklist

| Area | Finding |
|---|---|
| Correctness | **Scores at band edges** (24/25, 49/50, 74/75) fall in the right colour, using the same rule as `bandFor`. **Scores are always 0–100,** as the API guarantees. |
| Security | **No untrusted text** goes into the SVG; only numbers and the band label, inserted with `textContent`. |
| Performance | **One small SVG** per result; nothing new is downloaded. |
| Accessibility | **The level is in words** next to the gauge and in the `role="img"` label. **Motion** respects reduced-motion. |

### Alternatives considered
1. **A chart library:** a whole download for one dial. Rejected; about 40 lines of SVG do it.
2. **A full-circle dial:** it takes more height on a phone. The half circle reads more like a speedometer.

## Plan
Branch `feature/gauge` from `main`.

| # | What | Files | Tests | Done when |
|---|---|---|---|---|
| T1 | `gaugeSvg()`, used by `showScore`; CSS; reduced motion | `web/app.js`, `web/style.css`, `web/index.html` | Criteria 48–51 in headless Edge (scores 0, 25, 63 and 100; neighbourhood, street and walk; light, dark and phone screenshots) | Checks pass |
| T2 | E2E row; build and test records | `06-e2e-signoff.md` | Full suite and acceptance check | Pass |
| T3 | After your approval of phases 4–5: merge and deploy, then the production check | — | Acceptance check against production | Pass |

## What happens next
Once this is approved, I build T1–T2 and write `04-implementation.gauge.md` and `05-test-report.gauge.md`, with screenshots, for your approval.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
