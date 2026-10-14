# Phases 1–3 (addition): Odds as a percentage as well as "1 in N"

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-14  ·  **Status:** Approved  ·  **Builds on:** [01-03-odds.md](01-03-odds.md), [01-03-odds.r2.md](01-03-odds.r2.md)

## What this step is
A small addition: Sai asked (in chat, 2026-10-14) for the odds table to show a percentage next to each "1 in N" figure. This document combines the definition, design and plan for one approval.

## What was done
- Read the odds code: `scoring/odds.py` stores, for each severity level, the incidents and the "1 in N", and the neighbourhood and Toronto populations, in each neighbourhood's score details. `web/app.js` (`oddsNodes`) draws the table from those figures.
- Worked out the percentages from the live figures for Yonge-Bay Corridor (`100 Queen St W`, 2025), on the trends preview:

| Severity | Here now | Here with % | Toronto now | Toronto with % |
|---|---|---|---|---|
| High: serious violence | 1 in 110 | 1 in 110 (0.94%) | 1 in 470 | 1 in 470 (0.21%) |
| Medium: assault | 1 in 47 | 1 in 47 (2.1%) | 1 in 220 | 1 in 220 (0.45%) |
| Low: property crime | 1 in 46 | 1 in 46 (2.2%) | 1 in 140 | 1 in 140 (0.71%) |
| Any | 1 in 19 | 1 in 19 (5.2%) | 1 in 73 | 1 in 73 (1.4%) |

## Definition
**Goal:** each odds cell shows the "1 in N" with the same figure as a percentage after it, so readers who think in percentages can compare at a glance.

**Acceptance criteria:**
1. Every odds cell with incidents reads `1 in N (P%)`, for both the neighbourhood and Toronto, on search results and on neighbourhood clicks.
2. The percentage is incidents ÷ residents × 100, worked out from the unrounded counts, and shown to two significant figures (5.2%, 0.94%, 0.21%), matching the two-figure rounding of "1 in N".
3. "None reported" stays as it is, with no percentage.
4. The note under the table and the rules page say the percentage is per resident per year, and still not a personal chance.
5. The table still fits a phone screen (about 360 px wide) without sideways scrolling.

**Out of scope:** changing the odds themselves, the severity levels, or the API.

## Design
- **Only the web page changes.** The API already returns `incidents`, `toronto_incidents`, `population` and `toronto_population`, so `app.js` works the percentage out. No rebuild of the scores, no database change, and the API stays as it is.
- **Why the unrounded counts:** working from the rounded "1 in N" would show 0.91% instead of 0.94% for "1 in 110". The difference is small either way. The unrounded figure is the true one.
- **Wording.** Note under the table: "One reported incident a year for every N residents (P% of the population). Not a personal prediction: …" (the rest unchanged). The rules page adds one sentence: "The percentage is the same figure the other way round: reported incidents as a share of residents."
- **A concern to weigh:** a percentage reads more like a personal probability ("a 5% chance") than "1 in 19" does, especially for busy downtown areas where most incidents involve visitors. The note and rules page already say it isn't a personal prediction; keeping the "1 in N" first and the percentage in brackets keeps that framing.

## Plan
Built on a new branch, `feature/odds-percent`, from `main` after `feature/trends` is merged (both change `app.js`, so this avoids a merge conflict).

| # | Slice | Files | Check |
|---|---|---|---|
| P1 | `pct()` helper (two significant figures) and `1 in N (P%)` in the odds table; note wording | `web/app.js` | Headless Edge on the local server: `100 Queen St W` shows "1 in 110 (0.94%)" and "1 in 470 (0.21%)"; a level with no incidents shows "None reported"; table width at 360 px |
| P2 | One sentence on the rules page | `web/rules.html` | The sentence is under "Odds per resident" |
| P3 | Deploy a preview, check it, then ask before merging to `main` | | The same figures on the preview |

Then `04-implementation.odds-percent.md` and `05-test-report.odds-percent.md` for approval, and a new end-to-end row (43).

## What happens next
Once approved and `feature/trends` is merged, build P1–P3 on `feature/odds-percent`.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-14 13:07
- **User's response:** "yes sounds good i approve both" (after being offered a label for the score badge)
- **Revisions before approval:** Added at Sai's prompt, after asking "is the 15 the safety score or the odds score": criterion 6, the score badge carries a small label "Risk score (0–100, higher = riskier)" on search results and neighbourhood clicks, so it isn't mistaken for a safety score or the odds. Built in slice P1 (`web/app.js`, `web/index.html`, `web/style.css`). Walks get the same label.
