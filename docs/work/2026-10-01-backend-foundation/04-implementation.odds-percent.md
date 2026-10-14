# Phase 4 (addition): Odds as a percentage, and a "Risk score" label

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-14  ·  **Status:** Approved  ·  **Plan:** [01-03-odds-percent.md](01-03-odds-percent.md)

## What this step is
The build record for the approved plan: each odds cell shows a percentage after the "1 in N", and the score badge is labelled.

## What was done
Before building, with Sai's approval ("i approve both"), `feature/trends` was merged into `main` (`c6b6084`), as the plan required: 238 tests passed, the push deployed production, and `acceptance_check.py` against https://uavert.vercel.app passed **33 of 33**. Then a new branch, `feature/odds-percent`, was made from `main`.

| # | Slice | What changed | Commit |
|---|---|---|---|
| P1 | Percentage and label | `app.js`: `pct()` gives incidents ÷ residents × 100 to two significant figures; `oddsCell()` writes `1 in N (P%)`, and leaves "None reported" alone; the note now reads "One reported incident a year for every N residents (P% of the population). Not a personal prediction: …". `index.html` + `style.css`: a small muted line above the band, "Risk score (0–100, higher = riskier)". It is static, so it shows for addresses, neighbourhoods and walks | `0ded1d7` |
| P2 | Rules page | One sentence under "Odds per resident": the percentage is the same figure the other way round, worked out before rounding, for example 1 in 110 (0.94%) | `0ded1d7` |
| P3 | Preview | Branch pushed; Vercel builds a preview (see the test report) | |

9 lines changed in 4 files. No API, scoring or database change, so no score rebuild was needed.

## Checked in the browser
Headless Edge at 360 × 900 (phone size), local server, search `100 Queen St W`:
```
label: Risk score (0–100, higher = riskier)
badge: 63 Elevated risk
High: serious violence | 1 in 110 (0.94%) | 1 in 470 (0.21%)
Medium: assault        | 1 in 47 (2.1%)   | 1 in 220 (0.45%)
Low: property crime    | 1 in 46 (2.2%)   | 1 in 140 (0.71%)
Any                    | 1 in 19 (5.2%)   | 1 in 73 (1.4%)
page scrollWidth/clientWidth: [360, 360]   odds table width: 306 px
```
All eight figures match the plan's table. Screenshot: [screenshots/13-odds-percent-phone.png](screenshots/13-odds-percent-phone.png).

## Clean-up
The two helpers sit next to the existing `oneIn`, in the same one-line style. Nothing else touched.

## What happens next
Once approved: [05-test-report.odds-percent.md](05-test-report.odds-percent.md), then end-to-end row 43, then ask before merging to `main`.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-14 13:13
- **User's response:** "merge and i approve"
- **Revisions before approval:** none
