# Phase 4 (addition): Do the work: Odds alongside the score

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-07  ·  **Status:** Pending approval

## What this step is
The build record for the odds addition ([01-03-odds.md](01-03-odds.md), approved 2026-10-07 15:22) and its revision ([01-03-odds.r2.md](01-03-odds.r2.md), leave out incidents inside the two jails, approved 2026-10-07).

## What was done
Each slice was built with its tests written first and seen failing, then committed on `feature/backend-foundation`. Real-data checks were run against Neon `main` before the rebuild (a dry run that wrote nothing) and after it. The page was checked in headless Edge at laptop and phone widths. The branch was pushed and deployed to production from the branch, and nothing went to `main`.

## Plan steps
| # | Step | Result | Commit |
|---|---|---|---|
| O1 | `severity` column in the offence map; `OffenceMap.severities()` refuses an unknown level or one CSI offence given two levels | 2 tests; 204 passed | `00dc4e8` |
| O2 | `scoring/odds.py` (`one_in`, `by_level`, `odds`); neighbourhood score details carry the odds and Toronto's | 4 tests; 208 passed; dry run on real data (below) | `062c86c` |
| O3 | `odds` on `/risk-scores` (under `neighbourhood`) and `/neighbourhoods/{id}`; `null` when not stored | 3 API tests; 211 passed | `d95a4dc` |
| O4 | Odds panel on search results and the neighbourhood panel; "Odds per resident" section on the rules page | Screenshots: [laptop, light](screenshots/07-odds-laptop-light.png), [phone, dark](screenshots/08-odds-phone-dark.png) (page width 390 px, no sideways scroll), [rules page](screenshots/09-rules-odds.png) | `5f5b25d` |
| O5 | Acceptance check covers the odds (`odds-1`, `odds-1b`, `odds-3`) | 29 of 29 locally | `7ac1218` |
| O6 (r2) | `data/excluded_places.csv` (the two jails, 50 m, premises "Other"); `crime.at_excluded_place`; `load_events` leaves them out; rules page "Limitations" line; acceptance check `odds-r2` | 3 tests; 214 passed | `f2b3198` |
| O5 (rollout) | Rebuilt scores on Neon `main`; pushed the branch; `vercel deploy --prod` from the branch; acceptance check against https://uavert.vercel.app | "Scored 158 neighbourhoods and 5748 street cells from 53,207 distinct crime events" (54,636 before, minus 1,429 jail incidents); **30 of 30 checks passed** on the hosted site | deployed at `f2b3198` |

## Results on real data (hosted site, 2026-10-07)
| | High: serious violence | Medium: assault | Low: property | Any |
|---|---|---|---|---|
| Toronto (3,214,722 residents) | 1 in 470 | 1 in 220 | 1 in 140 | 1 in 73 |
| Yonge-Bay Corridor (16,661) | 1 in 110 | 1 in 47 | 1 in 47 | 1 in 19 |
| Mimico-Queensway, before r2 | 1 in 320 | 1 in 28 | 1 in 190 | 1 in 23 |
| Mimico-Queensway, after r2 (dry run) | 1 in 1,000 | 1 in 310 | 1 in 200 | 1 in 110 |

Scores after r2: Mimico-Queensway 40 → **24**, Clairlea-Birchmount 28 → **24** (both now "Lower reported risk"), as predicted in r2.

## Files changed
| File | New / changed | Summary |
|---|---|---|
| `data/offence_map.csv` | changed | `severity` column: high, medium or low for every offence |
| `data/excluded_places.csv` | new | The two jails: address, point, 50 m radius, premises "Other", reason |
| `src/uavert/ingest/reference.py` | changed | `severity` on each mapping; `OffenceMap.severities()`; `ExcludedPlace`, `load_excluded_places()` |
| `src/uavert/scoring/odds.py` | new | "1 in N" rounding, totals by level, the odds object |
| `src/uavert/scoring/crime.py` | changed | `at_excluded_place()` |
| `src/uavert/scoring/build.py` | changed | `load_events` reads locations and leaves out excluded places; `neighbourhood_scores` adds `details.odds` |
| `src/uavert/api/locate.py`, `api/routes/neighbourhoods.py` | changed | Return `odds` |
| `src/uavert/web/app.js`, `style.css`, `rules.html` | changed | Odds panel; rules page section and limitation |
| `scripts/acceptance_check.py` | changed | Checks `odds-1`, `odds-1b`, `odds-3`, `odds-r2` |
| `tests/test_odds.py`, `tests/test_excluded_places.py` | new | 7 tests |
| `tests/test_reference.py`, `tests/api/*` | changed | Severity tests; API odds tests; seeded odds for T1 |

## Deviations from the plan
1. **Toronto's figures differ from the plan's estimates:** 1 in 470 / 220 / 140 / 73 against 446 / 192 / 138 / 68 in 01-03-odds.md. The plan's figures came from a quick query that counted an event once per offence, while the build counts each event once, as the score does. Acceptance criterion 3 is checked against the build's figures.
2. **Odds are stored for every neighbourhood but the street cell isn't used,** as designed. No deviation, but note that the panel names the neighbourhood.
3. **The first `vercel deploy` attempt ended with a "retry deploy" suggestion** (its error wasn't captured). The second attempt completed ("readyState": "READY"), and the hosted check passed.
4. **The hourly GitHub Actions refresh** runs from this branch (`DATA_BRANCH`), so from now on it rebuilds the odds and leaves out the jails automatically.

## Clean-up
I reviewed the diff for reuse and simplicity:
- The odds reuse the neighbourhood score's own per-offence counts. Nothing is counted twice.
- The exclusion is one function, used in one place (`load_events`).
- No changes were needed.

## Follow-up ideas
- Other single addresses with many incidents (hospitals, shelters), if any turn out to matter. None is close in size today.
- Street-level per-visit odds, once foot-traffic data is better.
- Showing a severity column in the rules page's offence-map table.

## What happens next
Once approved, phase 5 verifies the work against every acceptance criterion and records it in `05-test-report.odds.md`. Then rows are added to the end-to-end checklist for you to test.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
