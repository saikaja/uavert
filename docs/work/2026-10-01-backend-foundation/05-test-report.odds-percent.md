# Phase 5 (addition): Test report: Odds as a percentage, and a "Risk score" label

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-14  ·  **Status:** Pending approval  ·  **Build:** [04-implementation.odds-percent.md](04-implementation.odds-percent.md)

## What this step is
Evidence that the change does what [01-03-odds-percent.md](01-03-odds-percent.md) says, and nothing else.

## Acceptance criteria
| # | Criterion | Result | Evidence |
|---|---|---|---|
| 1 | Every odds cell reads `1 in N (P%)`, here and Toronto | **Pass** | Headless Edge, `100 Queen St W`: all eight cells (see the build record). Neighbourhood clicks use the same `oddsNodes` code |
| 2 | Percentage from unrounded counts, two figures | **Pass** | 1 in 110 shows 0.94% (from the counts), not 0.91% (from 1/110); 5.2%, 2.1%, 0.21%, 1.4% match the plan |
| 3 | "None reported" has no percentage | **Pass (by reading the code)** | `oddsCell` returns `oneIn(n)` unchanged when `n` is null. No neighbourhood currently has a level with no incidents, so this couldn't be seen live |
| 4 | Note and rules page explain the percentage | **Pass** | Note: "…for every N residents (P% of the population). Not a personal prediction…"; rules page sentence served on the preview |
| 5 | Fits a 360 px phone screen | **Pass** | Page scroll width 360 = client width 360; odds table 306 px; [screenshot](screenshots/13-odds-percent-phone.png) |
| 6 | Badge labelled "Risk score (0–100, higher = riskier)" | **Pass** | Headless Edge read the label above "Elevated risk" |

## Other checks
- **Tests:** 238 of 238 pass (`pytest`). There are no automated tests for `app.js`; the browser check above covers it.
- **Preview:** https://uavert-2wlnj4cj1-sai-project.vercel.app (Vercel login needed). It serves the new `app.js` (`oddsCell` present), the label in `index.html` and the rules sentence; `/api/v1/risk-scores` for `100 Queen St W` answered 200 in 0.32 s. The API and scores are unchanged, so the 33-check acceptance run on production from earlier today still applies.

## Code review
| Area | Finding |
|---|---|
| Correctness | `toPrecision(2)` then `Number()` drops trailing zeros, so 0.10% would show as "0.1%". This is harmless and no current figure is affected |
| Security | Text is set with `textContent` via `el()`, never as HTML |
| Accessibility | The label is real text, read by screen readers before the band; muted colour matches `.score-sub`, which already passes contrast |
| Scope | 9 lines in 4 files; no API, scoring or data change |

## Could not verify
- A "None reported" cell on real data (criterion 3), as above.

## What happens next
Once approved: end-to-end row 43 is in [06-e2e-signoff.md](06-e2e-signoff.md). Then I'll ask before merging `feature/odds-percent` to `main`, which deploys production.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
