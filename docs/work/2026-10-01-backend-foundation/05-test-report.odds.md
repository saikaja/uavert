# Phase 5 (addition): Verify the work: Odds alongside the score

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-07  ·  **Status:** Approved

## What this step is
Proof that the odds addition ([01-03-odds.md](01-03-odds.md) and revision [01-03-odds.r2.md](01-03-odds.r2.md); built in [04-implementation.odds.md](04-implementation.odds.md), approved 2026-10-07) meets every acceptance criterion, before Sai's end-to-end testing.

## What was done
- Ran the full test suite.
- Rebuilt from a clean environment through the GitHub Actions refresh: it installs from scratch, checks out the branch, ingests and rebuilds the scores.
- Ran the scripted acceptance check against the local server and the hosted site.
- Loaded the page in headless Edge at laptop and phone widths, in both themes.
- Reviewed the whole diff since the plan (`09c121f..6fb11ee`) on five axes. One accessibility finding was fixed, redeployed and re-checked.

## Automated checks
| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `.venv\Scripts\python.exe -m pytest -q` | "214 passed in 54.92s", exit 0 |
| Linter / type checker | none is configured in this project (`ruff` isn't installed) | not run |
| Clean-environment rebuild | GitHub Actions "Refresh data", run `37677612784` (manual, `full=true`, ref `feature/backend-foundation`) | "success", 1m21s; log: "Scored 158 neighbourhoods and 5748 street cells from 53,207 distinct crime events." |
| Acceptance check, local | `scripts\acceptance_check.py http://localhost:8000` | "30 of 30 checks passed" |
| Acceptance check, hosted (after the final deploy) | `scripts\acceptance_check.py https://uavert.vercel.app` | "30 of 30 checks passed", exit 0 |

Compared with the baseline: 204 tests and 26 acceptance checks passed before this addition. All of them still pass, plus 10 new tests and 4 new checks.

## Acceptance criteria
| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | `/risk-scores` and `/neighbourhoods/{id}` return `odds` (each level: neighbourhood and Toronto "1 in N", year, population, counts) | `test_address_carries_its_neighbourhoods_odds`, `test_neighbourhood_detail_has_odds`; hosted `odds-1`, `odds-1b` | Pass |
| 2 | 1 in N = population ÷ incidents (homicides as a 3-year average), 2 significant figures from 100; "None reported" when zero | `test_one_in_rounds_to_two_significant_figures_from_100`, `test_one_in_is_none_without_incidents_or_residents`, `test_neighbourhood_odds_per_resident_with_toronto_alongside` (homicide counted as 0.3) | Pass. The UI says "None reported", with the year in the table heading rather than in each cell |
| 3 | Toronto figures match the database | hosted `odds-3`: "Toronto 2025: any 1 in 73, high 1 in 470, low 1 in 140, medium 1 in 220" | Pass, against the build's counts (each event counted once). The plan's estimates (446/192/138/68) were from a rougher query; see deviation 1 in the build record |
| 4 | Panel on search results and the neighbourhood panel; laptop and phone; light and dark | Screenshots [07](screenshots/07-odds-laptop-light.png) (search, laptop, light), [08](screenshots/08-odds-phone-dark.png) (search, phone, dark; page width 390 px), [10](screenshots/10-odds-neighbourhood-laptop-dark.png) (neighbourhood panel, laptop, dark), [11](screenshots/11-odds-mimico-phone-light.png) (search, phone, light) | Pass |
| 5 | Never "safe" or "chance of being a victim"; always names the year and "reported" | `git diff 09c121f -- src/uavert/web` searched for "safe" and "chance": the only match is the rules page saying the odds are "**not** anyone's personal chance of being a victim". Heading "Odds in … (2025)"; note "One reported incident a year…" | Pass |
| 6 | Score, bands and existing reasons unchanged by the odds | All 204 earlier tests and 26 earlier acceptance checks still pass. Scores changed only through r2 (criterion 9), as approved | Pass |
| 7 (r2) | Premises "Other" within 50 m of either jail left out; outdoor incidents and homicides still count | `test_inside_a_jail_is_left_out`, `test_outdoors_or_further_away_still_counts`; 54,636 → 53,207 events (−1,429, matching the count in r2) locally and in the clean rebuild | Pass |
| 8 (r2) | Rules page names the places and why | `rules.html` "Limitations": "Incidents recorded inside Toronto's two jails (Toronto South Detention Centre, 130 Horner Ave, and Toronto East Detention Centre, 55 Civic Rd) are left out…" | Pass |
| 9 (r2) | Mimico-Queensway 24, Clairlea-Birchmount 24 | hosted `odds-r2`: "Mimico-Queensway 24 with jail incidents left out (was 40)"; local API: "Mimico-Queensway 24 lower", "Clairlea-Birchmount 24 lower" | Pass |

## Real-app checks
- **Hosted site:** after the final deploy (`uavert-hq7q5qw01`, aliased to uavert.vercel.app, "readyState": "READY"), the acceptance check passed 30 of 30. A fresh request for `app.js` returns the scope fix. The first request returned a cached copy from just before the alias switched.
- **Browser:** the table text read from the page for Mimico-Queensway is "High: serious violence 1 in 1,000 1 in 470 · Medium: assault 1 in 310 1 in 220 · Low: property crime 1 in 200 1 in 140 · Any 1 in 110 1 in 73". The header cells read "col,col,col,row,row,row,row".

## Code review findings
| # | Finding | Action |
|---|---|---|
| 1 | Accessibility: the odds table's header cells had no `scope`, so screen readers couldn't pair a figure with its row and column | **Fixed** in `6fb11ee`. Checked in the browser (scopes "col,col,col,row,row,row,row"), redeployed, and the hosted check passed again |
| 2 | Correctness: Python rounds halves to even, so an exact 1,250 shows as "1 in 1,200" rather than 1,300 | Accepted: it only happens on exact halves and is within the stated rounding |
| 3 | Readability: `/neighbourhoods/{id}` returns the odds both as `odds` and inside `crime_details.odds` | Accepted: `crime_details` is the raw stored record, and `odds` is the documented field |
| 4 | Security: all odds text reaches the page through `textContent`, so nothing can inject HTML. No new inputs and no new outside calls | No action |
| 5 | Performance: the odds are computed at build time and read with the existing query (one more JSON field). The build took about 12 s, as before | No action |
| 6 | Architecture: the severity levels and excluded places live in reference CSVs next to the offence map, and the scoring code has no hard-coded list | No action |

## Could not verify
- **A real person reading the panel:** whether the wording is clear and the downtown caveat lands. This goes to Sai's checklist (rows 35–38).
- **A real phone:** checked at phone width in headless Edge, not on a device. This goes to the checklist.

## What happens next
Once approved, Sai tests rows 35–38 in [06-e2e-signoff.md](06-e2e-signoff.md), along with the earlier rows that are still open.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-07 15:56
- **User's response:** "yes"
- **Revisions before approval:** none
