# 5. Verify the work (fairer scores, crowds, extreme heat): Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval

## What this step is
This step checks criteria 40–51 from [01-03-calibration-crowds-heat.md](01-03-calibration-crowds-heat.md) with evidence, and re-checks the earlier criteria on local and hosted.

## What was done
- Ran the full test suite after each step.
- Ran the live acceptance check (`scripts/acceptance_check.py`, now 26 checks) against the local server and https://uavert.vercel.app after the production deploy.
- Ran the GitHub Actions refresh by hand.
- Checked the real data at each step.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | `202 passed`, exit code 0 |
| Lint | `python -m pyflakes src tests` | no output (no issues) |
| Web code syntax | `node --check src/uavert/web/app.js`; rules script parsed | ok |
| Live acceptance check, local | `python scripts/acceptance_check.py` | `26 of 26 checks passed` |
| Live acceptance check, hosted | `python scripts/acceptance_check.py https://uavert.vercel.app` | `26 of 26 checks passed` |
| Scheduled refresh (manual run) | GitHub Actions `36939044532` (full) | "✓ refresh in 1m30s" |

**Compared with the last report:** 164 → 202 tests. Every earlier test still passes, apart from the intended updates: tests that asserted the old ranking scale, and the yellow test warning now made red.

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 40 | Formula: 1× → 25, 2× → 45, 4× → 65, 8× → 85, 0.25× → 0, 64× → 100 | `test_relative_score_formula` (7 cases), `test_relative_score_handles_zero`. Live: "scale: 25 at a typical Toronto block or neighbourhood (the median), +20 per doubling" | Pass |
| 41 | Union Station → 125 Blue Jays Way all day is about 50–55, not High; a reason gives the × typical figure; band shares recorded | Hosted and local: "score 53 elevated (was 80-84 high), typical 35 moderate". Reason: "About 2.7× the reported street crime per person of a typical Toronto block…". Shares: 49 / 28 / 16 / 7 % | Pass |
| 42 | The order of places is unchanged | Real data: "score inversions when sorted by underlying value = 0". Fairness unchanged at −0.283 / +0.236. `test_scores_keep_the_order_of_places`. (Capped scores tie, so the exact rank correlation is just under 1.0; see deviation 1 in the build record) | Pass (as described) |
| 43 | City Hall scores higher at 2 am than at 2 pm | Live: "City Hall street score 2 am 100 > 2 pm 69" | Pass |
| 44 | The walk returns `typical_score` and `typical_band` | `test_typical_score_is_the_length_weighted_median`; API `test_route_score_is_highest_along_route_with_riskiest_stretches`; live "walk has typical_score and typical_band" | Pass |
| 45 | A street block's first reason is its most frequent offence | `test_first_street_reason_is_the_most_frequent_offence`. Live: the walk's first reason is "277 assaults within about 250 m…" | Pass |
| 46 | Alert levels follow the colours | `test_alert_level_follows_environment_canada_colours` (9 cases), `test_routine_yellow_heat_warning_is_moderate_not_high`, `test_red_warning_puts_area_in_high_band_and_names_alert`. Live `/scoring-rules`: "alert colours {'yellow': 40, 'orange': 65, 'red': 90}" | Pass |
| 47 | Cool spaces loaded with hours and `collected_at` | `ingest heat`: "toronto_cool_spaces: 478 cool spaces" (and the same on GitHub Actions). `test_parse_real_rows_with_hours_call_and_none` (5 real rows, including "CALL" and "None" hours) | Pass |
| 48 | During a heat alert, the nearest cool space open at that time is named; none without a heat alert | `test_open_status`, `test_nearest_open_prefers_an_open_place_and_skips_closed_ones`, `test_heat_reason_text`. API: `test_heat_alert_names_the_nearest_open_cool_space` (noon: "Test Library … open until 8:30 pm"), `test_late_at_night_nothing_is_open`, `test_no_heat_alert_no_cool_space_reason` | Pass (test data; no real heat alert during testing) |
| 49 | Venue list with sources; venue reason with no score change | `test_venue_list_has_sources`, `test_venue_is_context_only`; API `test_venue_is_context_with_no_score` ("Near Test Stadium: can draw about 40,000 people on event days", crowds 0) | Pass |
| 50 | Large City events found by date; crowds 35 within 1 km on the date only | `test_event_raises_crowds_to_moderate_on_its_date_only`, `test_spin_offs_count_only_on_the_main_event_dates_and_duplicates_collapse`, `test_main_event_with_various_location_uses_the_default`; API `test_event_today_raises_crowds_nearby`. **Live:** Nuit Blanche 2026 stored for 2026-10-03 and 2026-10-04 at Nathan Phillips Square | Pass |
| 51 | "Crowds" is in every score's categories and combines like the others; the rules page explains it | API `test_crowds_category_in_cells`; live "categories: ['alert', 'crime', 'crowds', 'environment', 'news']"; rules page screenshot `screenshots/06-rules-fairer-scale.png` | Pass |

**Earlier criteria:** all 22 earlier live checks still pass, both local and hosted. Criteria 12 and 13 now answer in 0.1–0.6 s, helped by the saved lookups.

## Real-app checks
- **Production:** deployed to https://uavert.vercel.app (deployment `uavert-r62fyr0ip`), then checked with the acceptance script: 26 of 26.
- **`main` doesn't auto-deploy:** pushing the workflow update to `main` created no production deployment (`vercel ls` showed only previews), and the live site stayed healthy.
- **GitHub Actions:** a full manual run passed, including the 26,402-entry events calendar and the 478 cool spaces.

## Code review findings
Issues found while building and checking real data, all fixed and tested:
- a "Various" location geocoded to Alberta
- duplicate calendar entries
- a spin-off event counted on the wrong day
- an over-strict venue test, adjusted after checking the real reasons

No separate review agent was run.

## Could not verify
These go into the phase 6 checklist:
1. **A real heat warning.** None was active (it's October), so this was tested with test data only.
2. **Nuit Blanche on the night.** It runs October 3–4. Checking the map near City Hall on Saturday evening should show "Nuit Blanche 2026 today… large crowds" (row 33).
3. **The map in a browser:** the walk panel's "mostly …" line, the "Crowds" bar, and the rules page sections. They render (screenshot), but nobody has clicked through them.

## What happens next
Once this and the build record are approved, run the new rows of the phase 6 checklist.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
