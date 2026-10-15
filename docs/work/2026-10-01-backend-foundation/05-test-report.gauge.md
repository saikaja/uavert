# 5. Verify the work: the risk score as a speedometer gauge

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Approved
**Verifies:** [01-03-gauge.md](01-03-gauge.md), criteria 48–51, built in [04-implementation.gauge.md](04-implementation.gauge.md).

## What this step is
This is the evidence that the gauge shows the right score in the right colours everywhere, and that nothing else on the page broke.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite (server code unchanged) | `python -m pytest -q` | "311 passed in 84.92s" (exit code 0) |
| Gauge browser check (headless Edge, local app on the real data as `uavert_web`) | scratch script, 14 checks | "14 of 14 browser checks passed" |
| Earlier time-of-day browser check, same app | scratch script | "17 of 18". The one difference is expected: that old check read the square badge's red background, which the gauge replaces (it now reads `rgba(0, 0, 0, 0)`). The gauge check covers the colours instead. |
| Earlier news browser check, same app | scratch script | "13 of 13 browser checks passed" |

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 48 | A gauge for neighbourhoods, street blocks and walks; sections in the `BANDS` colours; needle at `score / 100 × 180°` | "four sections in the map colours, in order: lower #2e9e57, moderate #f2c230, elevated #e8792b, high #c62828". Needle measured from the page at 0 → 0°, 25 → 45°, 63 → 113.4° and 100 → 180°. Kensington-Chinatown 55 → 99°. Street block: "Risk score 24 out of 100: lower reported risk". Walk: "Risk score 75 out of 100: high risk; 135 deg". | Passed |
| 49 | The number is text in `#score-badge`; `role="img"` with a label | "neighbourhood shows the gauge with its score as text: 55 / Risk score 55 out of 100: elevated risk". The aria label matches the score and band. | Passed |
| 50 | Fits and reads in both themes and on a phone | Dark mode: needle and number `rgb(236, 238, 241)` on the card `rgb(30, 33, 37)`. Light mode: screenshot `gauge-1-neighbourhood-light.png`. Phone (390 px): no sideways scrolling, screenshot `gauge-4-phone-dark.png`. One screenshot per band (`gauge-2-0-lower` … `gauge-2-100-high`). | Passed |
| 51 | No console errors; earlier browser checks still pass | "no console errors (apart from the existing missing favicon)". Earlier checks as listed above. | Passed |

**Reduced motion:** with `prefers-reduced-motion: reduce`, the needle's transition is "0s".

## Code review findings

| # | Finding | Action |
|---|---|---|
| 1 | The old check for the badge's red background no longer applies | Expected; replaced by the gauge's colour checks |
| 2 | **Security:** the SVG uses only numbers and the fixed band labels, inserted with `textContent` and `createElementNS` | No action |
| 3 | **Clean-up:** the old badge colour classes became unused | Removed |

## Could not verify
These go to your test list (row 53):
- **The hosted site:** after your approval.
- **A real phone.**
- **Whether the gauge reads clearly to you.**

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-15 15:39
- **User's response:** "approve"
- **Revisions before approval:** none
