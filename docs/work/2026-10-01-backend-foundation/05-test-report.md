# 5. Test the work: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved

## What this step is
This step checks every acceptance criterion with real evidence before you test it yourself (phase 6). It covers:
- the original build
- design revisions 2 and 3 (foot traffic and stand-out stretches)
- the time-of-day addition (criteria 21–28)

## What was done
1. **Ran every automated check:** tests, lint, a syntax check of the web code and a compile check.
2. **Followed the README from scratch** in a fresh copy of the repository. This was against a **new, empty database** (`fresh_check`, created on the Neon `test` branch so the real data was not touched), to check criterion 1 exactly as worded.
3. **Ran the real app** against the real database and the live outside services, using `scripts/acceptance_check.py`. This script calls the running server over HTTP and prints evidence and timings for each criterion.
4. **Reviewed the whole branch** with the `code-review` skill at high effort. Then fixed the findings, added regression tests, and ran everything again.

All results below are from runs on 2026-10-01, between about 13:35 and 13:55 Toronto time. Final commit: `6753b17`.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | `148 passed in 40.59s`, exit code 0 |
| Unit tests only | `python -m pytest -q -m "not db"` | `91 passed, 51 deselected` (before the review's regression tests were added) |
| Database and API tests | `python -m pytest -q -m db` | `51 passed, 91 deselected` (same timing) |
| Test suite in a fresh copy | in the clean clone: `python -m pytest -q` | `142 passed in 17.69s` (before the regression tests) |
| Lint | `python -m pyflakes src tests scripts` | no output (no issues) |
| Web code syntax | `node --check src/uavert/web/app.js`; rules page script parsed | `app.js ok`, `rules.html script ok` |
| Compile | `python -m compileall -q src scripts` | `compileall ok` |

**Compared with the baseline:** the baseline in `03-plan.md` was an empty project with no tests, so there were no earlier passing tests that could break. Every test added during the build passes.

## Acceptance criteria
"Live" means checked against the running server and real data with `scripts/acceptance_check.py`, or with the commands named. Test names refer to `tests/`.

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | Empty database → 158 neighbourhoods, boundaries, 2025 rates and 12+ months of incidents; re-run adds no duplicates | Clean clone + empty `fresh_check` database. `migrate` applied 4 migrations; `ingest all` took 1 min 3 s. Counts: neighbourhoods **158**, cells 5,748, incidents **58,072** rows (MCI 62,227 / shootings 379 / homicides 61 records fetched, matching the service totals), **54,487** distinct events. Second and third `ingest all`: every count identical; `ingest_runs` grew 11 → 22 → 33. Also `test_rerun_adds_no_duplicates_and_keeps_collected_at` | Pass |
| 2 | CSI weights stored with source and edition; every offence mapped; unknown offence stops with a clear error | Live `/scoring-rules`: "CSI edition 2009, 26 weights, 24 mappings". The real load mapped every offence since 2025-01-01 without error. Tests: `test_all_offences_seen_in_last_12_months_are_mapped`, `test_unmapped_offence_stops_with_its_name`, `test_unmapped_offence_stops_the_load` | Pass |
| 3 | Current AQHI and the current alert set stored (an empty set is allowed) | Live: "eccc_aqhi: 6 station readings"; "eccc_alerts: 0 alerts covering the Toronto area" (none active). Tests: `test_parse_real_aqhi_response`, `test_parse_real_warning` | Pass |
| 4 | Each source has name, licence, attribution, last refresh; `/sources` returns them | Live: "11 sources, each with name, licence, attribution", all with status. Fresh database: "rows missing collected_at: 0". Tests: `test_sources_list_freshness`, `test_every_data_table_records_collection_time`, `test_meta_lists_data_date_and_collection_time_per_source` | Pass |
| 5 | Neighbourhood crime score = percentile of the CSI-weighted rate | `test_weighted_rate_uses_csi_weights` (hand-worked 6,980), `test_percentile_rank_hand_worked`, `test_neighbourhood_scores_rank_csi_weighted_rates_and_explain_them` | Pass |
| 6 | Street cells: street premises only, recency, leaning toward the neighbourhood | `test_only_street_premises_count` (8 cases), `test_recent_incidents_weigh_more`, `test_sparse_cell_leans_toward_neighbourhood`, `test_cell_scores_count_street_incidents_nearby_and_lean_when_sparse`. Revision 3 adds per person: `test_cell_scores_allow_for_foot_traffic`, `test_per_person_uses_floor_of_100` | Pass |
| 7 | Combined = highest category, never an average | `test_combined_is_highest_not_average` | Pass |
| 8 | An active official alert puts covered areas in "high" and is named in the reasons | `test_warning_puts_area_in_high_band_and_names_alert`; API `test_warning_moves_covered_neighbourhood_to_high`. As designed, "official alert" means a warning or an orange/red alert. **No alert was active in Toronto during testing**, so this is proven with test data only (see Could not verify) | Pass (test data) |
| 9 | "safe" is never a label | `test_bands`, `test_no_response_labels_anything_safe`; live: "no band or label containing 'safe' in 5 live responses" | Pass |
| 10 | `/neighbourhoods` returns 158 with score, band, categories, GeoJSON; detail gives 2–3 reasons with source and date | Live: "158 neighbourhoods with score, band, categories, GeoJSON"; "Agincourt North: 3 reasons, e.g. '20 robberies reported in 2025 (67 per 100,000 residents; Toronto median 53)'" | Pass |
| 11 | Cells endpoint for a map area | Live: "65 cells in 1.34s, e.g. score 95, 599 incidents". Tests: `test_cells_in_bbox`, `test_cells_bad_bbox` (3 cases) | Pass |
| 12 | Destination `100 Queen St W, Toronto` in under 2 s | Live, cold cache: **0.84 s** on the first run and **0.49 s** after the fixes; "street 84 high, neighbourhood Yonge-Bay Corridor 100" | Pass |
| 13 | Walking route (Union Station → Kensington Market) in under 3 s, with the highest-score rule and up to 3 stretches | Live, cold cache: **2.38 s** (both runs); "2840 m, score 95 high, 1 stand-out stretch". Stretches follow revision 2 (stand out from surroundings). Tests: `test_route_score_is_highest_along_route_with_riskiest_stretches`, `test_standout_stretches_ranked_thresholded_and_joined`, `test_route_where_nothing_stands_out_says_so` | Pass |
| 14 | Outside Toronto, not found or not routable → clear 4xx | Live: Mississauga → "422 outside_coverage"; nonsense → "404 address_not_found"; Union → Scarborough → "422 … 17.6 km apart; walking routes are limited to 10 km". Tests: `test_destination_errors`, `test_route_errors` (no_route, upstream 502, too long) | Pass |
| 15 | News stored and labelled; `/news-events` lists them | Live: CBC "20 stories read, 0 labelled" (correct: today's stories are elections, housing and collisions outside Toronto); GDELT "1 stories read, 0 labelled". Tests: `test_none_of_todays_real_cbc_stories_is_flagged`, `test_classify_and_extract_place` (12 cases), `test_store_locates_toronto_stories_and_skips_unlabelled`, `test_news_events_lists_recent_reports_unverified`. **No real positive story was available during testing** (see Could not verify) | Pass (with test data for positive stories) |
| 16 | News raises nearby cells, is labelled unverified, expires in 24 h, never goes above "elevated" | `test_news_raises_nearby_cells_and_fades_over_24_hours` (74 → 37 → 0), `test_news_reason_is_labelled_unverified_with_link`, `test_news_alone_never_reaches_high`, `test_located_report_raises_its_neighbourhood_with_unverified_reason` | Pass |
| 17 | A source being down keeps old data, reports the failure, and the API still serves | **Real case:** GDELT returned HTTP 429 during the fresh-database load; the other 6 steps finished and the CLI reported "1 step(s) failed: news_gdelt. Previously stored data was kept." Tests: `test_failed_fetch_keeps_old_rows_and_records_failure`, `test_failed_traffic_download_keeps_stored_counts`, `test_geocoder_down_is_502`, route upstream 502 | Pass |
| 18 | No secrets in the repository; `.env` ignored | Scan of all tracked and untracked files for Neon passwords and connection strings: "none" (apart from a made-up `postgresql://u:p@h/d` in a settings test). `git check-ignore -v .env` → `.gitignore:1:.env`. Personal email in code or data: "none" | Pass |
| 19 | The web map shows neighbourhoods, a street layer, details, destination and route, news | Live: `/` 200, `/rules.html` 200, `/api/docs` 200. Headless Edge screenshots of the map, the rules page and the time selector are in `screenshots/`. **Clicking, zooming, searching and drawing routes in a browser were not automated** (see Could not verify) | Partly verified; rest goes to phase 6 |
| 20 | One-command tests; the README explains set up, ingest, run, test | `python -m pytest` 148 passed. The README was followed step by step in a clean clone. **This found a real bug, now fixed:** `build-scores` crashed on a fresh Windows install (no time-zone data). Fix: `tzdata` is now a declared dependency (`a0ad5f1`); the clean run then succeeded | Pass (after fix) |
| 21 | `hour` optional (0–23); without it, unchanged; out of range → 422 | Live: no hour → "All day"; `hour=24` → "422 validation_error". Tests: `test_without_hour_responses_are_all_day`, `test_bad_hour_is_422` (24, −1, "late") | Pass |
| 22 | Fewer people out → higher score for the same incidents | `test_fewer_people_out_means_higher_risk_per_person`, `test_hourly_scores_rise_when_streets_empty` | Pass |
| 23 | Few incidents → follows the city's hourly pattern | `test_few_incidents_follow_the_city_pattern` | Pass |
| 24 | Untimed incidents (homicides) spread evenly | `test_window_shares_and_untimed_incidents_spread_evenly`, `test_local_hour_and_homicides_without_time` | Pass |
| 25 | City Hall at 2 am scores higher than at 2 pm | Live: "City Hall street score 2 am 99 > 2 pm 87" | Pass |
| 26 | The time reason names incidents vs average, foot traffic vs daytime, measured or estimated | Live: "At 2 am: incidents near here run at about 0.8× this block's average, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)". Test: `test_hour_changes_street_score_and_explains_it`, `test_daytime_hour_says_measured` | Pass |
| 27 | Activity table records sources and dates; `/sources` lists it | Live: "activity_profile as_of 2025-12-31…, collected 2026-10-01T17:23…". Test: `test_activity_profile_has_24_hours_sources_and_dates` | Pass |
| 28 | Time selector updates the street layer, destination and route; says which time is shown | Code in place; screenshot `03-map-with-time-selector.png` shows the selector. **Changing it in a browser was not automated** (see Could not verify) | Goes to phase 6 |

**Revision 2 and 3 checks** (from their test strategies): all pass.
- `test_parse_real_sample_normalises_to_per_hour`
- `test_parse_skips_rows_without_coordinates_and_keeps_latest_per_location`
- `test_foot_traffic_widens_search_then_falls_back_to_city_median`
- `test_surroundings_ratio`
- `test_busy_area_threshold_is_90th_percentile`
- the stand-out stretch tests
- the live downtown walks reported in `04-implementation.md`

## Real-app checks
1. **From empty, following the README:**
   - fresh clone and `uv` setup
   - `migrate` (4 migrations, 2 s)
   - `ingest all` (1 min 3 s): Toronto Police 62,227 + 379 + 61 records, 6,394 traffic counts, 6 AQHI readings, 0 alerts, 20 CBC stories; GDELT refused with 429 and was reported
   - `build-scores` (7.8 s, after the tzdata fix): "Scored 158 neighbourhoods and 5748 street cells from 54,487 distinct crime events"
   - two more full loads: no duplicates; every row has `collected_at`; all 5,748 cells have 24 hourly scores
2. **Live server** (`python -m uavert serve`) against the real database: `scripts/acceptance_check.py` reported "22 of 22 checks passed", both before and after the review fixes. Timings are in the table above. The first health call took about 2.1–2.4 s, because Neon was waking from sleep (as expected).
3. **Live refresh before the final run:** `ingest live`: AQHI 6, alerts 0, CBC 20 read / 0 labelled, GDELT 1 read / 0 labelled (it answered this time).
4. **Screenshots:** the map, the rules page and the time selector, taken in headless Edge against the live server.

## Code review findings
`code-review` at high effort over the whole branch raised 10 findings. Each was checked against the code. Eight were fixed in `6753b17` with regression tests; one was partly fixed; one was recorded as a limitation.

| # | Finding | Action |
|---|---|---|
| 1 | Re-collecting a news story wiped its location if geocoding failed or found no place that time | **Fixed:** the stored location is kept (COALESCE), and already-located stories aren't geocoded again. Test: `test_news_rerun_keeps_location_and_skips_geocoding` |
| 2 | An alert cancelled early (dropped from the feed) stayed "active" until it expired, or forever | **Fixed:** alerts missing from the current feed are marked ended. Test: `test_alert_withdrawn_from_feed_is_marked_ended` |
| 3 | A crime source returning no records crashed the progress line and marked the source failed | **Fixed.** Test: `test_crime_source_with_no_records_does_not_crash` |
| 4 | `build-scores` with no street incidents crashed with an unclear error | **Fixed:** it now says "Run `uavert ingest crime` first". Test: `test_build_without_street_incidents_says_what_to_do` |
| 5 | The request limit (30 per minute) also counted map clicks by coordinates, which call no outside service | **Fixed:** the limit applies to address lookups only. Test: `test_map_clicks_by_coordinates_are_not_rate_limited` |
| 6 | A slow earlier street-layer response could replace a newer one (for example after quickly changing the time) | **Fixed:** stale responses are ignored. Checked by syntax only; the behaviour goes to the phase 6 checklist |
| 7 | News links from outside feeds were used as links unchecked (a `javascript:` URL could run script), and map tooltips rendered names as HTML | **Fixed:** only http(s) links are stored and shown, and tooltips are escaped. Test: `test_news_ignores_non_web_links` |
| 8 | The request-limit memory and the geocoding cache grew without limit in a long-running server | **Fixed:** expired entries are pruned |
| 9 | `PROJECT_ROOT` only works from a source checkout; a non-editable `pip install .` would miss `data/` and migrations | **Not fixed (limitation):** the README installs with `-e` (editable), which works. Packaging data into the wheel is a follow-up for deployment |
| 10 | Every request reloads live context; the AQHI query scans all history | **Partly fixed:** the AQHI lookup is limited to 2 days, and the rules endpoint reuses loaded data. A short-lived shared cache is a follow-up for production load |

**Also found and fixed during testing:**
- **Missing `tzdata`** (criterion 20 above).
- **My own mistake in fix 10:** the first version of the AQHI change failed on every request (Postgres couldn't tell the parameter's type). The full test suite caught it immediately (23 failures), and it was fixed before commit.

## Could not verify
These go into the phase 6 checklist for you:
1. **Using the map in a browser:**
   - clicking neighbourhoods and blocks
   - zooming into the street layer
   - destination search
   - drawing a walk and its stand-out stretches
   - changing the time selector, which should re-run the search
   - the phone layout

   Pages load and render (screenshots), but the clicks and typing were not automated.
2. **A real official warning.** None was active in Toronto during testing, so warnings were proven with test data only.
3. **A real news story about a Toronto protest or violent incident.** None appeared in the feeds today. Labelling and locating were proven with made-up examples and 20 real negative stories.
4. **Timing on your network and at demo time.** Lookups depend on free outside services (Nominatim, OSRM) and on Neon waking up (about 2 s for the first request). Run `scripts/warm_demo.py` before presenting.
5. **A non-editable install** (`pip install .` without `-e`): not supported yet (finding 9).

**Left in place:** the empty test database `fresh_check` on the Neon `test` branch. It is harmless; deleting it is a destructive action, so I haven't done it without asking.

## What happens next
Once this is approved, phase 6 (hand-off) gives you:
- the exact commands to run the app
- a step-by-step checklist built from the acceptance criteria, including the "Could not verify" items above
- a demo-day routine for Tuesday

You run it yourself and record the results.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 13:52
- **User's response:** "approved"
- **Revisions before approval:** none
