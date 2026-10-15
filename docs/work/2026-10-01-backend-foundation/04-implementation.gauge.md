# 4. Do the work: the risk score as a speedometer gauge

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Builds:** [01-03-gauge.md](01-03-gauge.md) (approved 2026-10-15, "approve and we can do the sertting later").

## What this step is
This records how the approved plan was built.

## What was done
- **Branch:** `feature/gauge`, from `main` at `042af78`. Two steps, each committed. Page code only; no server or database change.
- **Testing:** checked in headless Edge against the app running locally on the real data, connected as the read-only `uavert_web`.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | `gaugeSvg()` and `setGauge()` in `app.js`, used by `showScore` for neighbourhoods, street blocks and walks; CSS for the dial, needle, number and reduced motion | 14 of 14 gauge checks. Screenshots `gauge-1` to `gauge-4` in [screenshots/](screenshots/). | `7e01d99` |
| T2 | Removed the now-unused badge colour classes; E2E row 53 | Full suite 311 passed. | `845ae4d` |
| T3 | Merge, deploy, production check | Waits for your approval | — |

## How it works
- **The dial:** an inline SVG, 132 × 80, built with `createElementNS` (no HTML strings):
  - four arcs, one per band, with the band limits 0/25/50/75/100 (the same as `bandFor`) and the colours read from `BANDS`, the constant the map uses
  - marks at 0, 25, 50, 75 and 100
- **The needle:** drawn pointing at 0 and turned by `score / 100 × 180°` with a CSS rotation, so it swings in 0.4 s. `prefers-reduced-motion` turns the swing off.
- **The number:** under the hub, in `#score-badge`, so it's still plain text. The box has `role="img"` and a label such as "Risk score 55 out of 100: elevated risk".
- **Reuse:** the SVG is built once and reused, so when a new score arrives (a time change, another place) the needle swings from its last position.

## Files changed

| File | Change |
|---|---|
| `src/uavert/web/app.js` | `GAUGE`, `BAND_RANGES`, `gaugePoint()`, `gaugeSvg()`, `setGauge()`; `showScore` uses them |
| `src/uavert/web/style.css` | Gauge styles; reduced motion; the `.b-*` badge colour classes removed |
| `06-e2e-signoff.md` | Row 53 |

## Deviations from the plan
None.

## Clean-up
- **Unused CSS:** the four `.b-lower` … `.b-high` classes, used only by the old square badge, were removed (searched: no other use).
- **One place for colours:** the dial reads its colours from `BANDS`, so map and gauge can't differ.

## Follow-up ideas
None.

## What happens next
Once you approve this and [05-test-report.gauge.md](05-test-report.gauge.md), I merge `feature/gauge` into `main`, which deploys, and check production.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
