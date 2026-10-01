# 4. Do the work: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved

## What this step is
This step builds the approved plan ([03-plan.md](03-plan.md)) step by step, with tests written alongside the code. It then runs a clean-up pass. This document records what was built and where it differs from the plan.

**Updated 2026-10-01:** when this document first went to the user for approval, they asked for the downtown issue (follow-up 1) to be tackled first. This led to two approved design revisions, built on the same branch:
- [02-design.r2.md](02-design.r2.md): compare each block with its surroundings
- [02-design.r3.md](02-design.r3.md): allow for foot traffic

They are recorded under "Additions from design revisions 2 and 3" below.

## What was done
- **All 14 plan steps** were built in order on the branch `feature/backend-foundation`. After each step the tests passed and the step was committed. A final clean-up commit followed.
- **Test suite:** `python -m pytest` reports **127 passed**: 116 before the revisions, 11 added with them.
  - Unit tests cover the scoring rules, data parsers, news labels and route stretches.
  - API tests run against the Neon `test` branch with a small made-up dataset.
  - Outside services are faked in tests.
- **Real data:** loaded into the Neon `main` branch on 2026-10-01:
  - Toronto Police: 62,227 Major Crime Indicators records, 379 shootings and 61 homicides since 2025-01-01. These match the service's own totals.
  - 54,487 distinct events after counting each event once.
  - 158 neighbourhoods and 5,748 street cells, scored.
  - Live AQHI from 6 stations, current weather alerts (none active for Toronto) and today's CBC Toronto news.
- **Live checks** on the real data, with the app running in-process (full results in phase 5):

  | Check | First call | Repeat call |
  |---|---|---|
  | Destination: `100 Queen St W, Toronto` | 0.7 s | 0.2 s (cached) |
  | Route: Union Station → Kensington Market (2.8 km) | 2.2 s | 0.4 s |
  | All 158 neighbourhoods | 0.6 s | |
  | A street-level map view | 0.2 s | |

- **Checkpoint after step 7:** the ranking comparison report, [csi-vs-demo-ranking.md](csi-vs-demo-ranking.md), was produced and shared.
- **Web map:** checked in headless Edge. Screenshots are in [screenshots/](screenshots/).
- **Demo warm-up:** `scripts/warm_demo.py` ran against the live server, and all 9 checks returned 200.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| 1 | Project skeleton, settings, migrations runner, health endpoint | Done | `9123844` |
| 2 | Schema with `collected_at` on every data table, `ingest_runs` history | Done | `ec7bb99` |
| 3 | HTTP client (timeouts, retries), ArcGIS paging, Toronto Police parsers | Done | `c19fede` |
| 4 | CSI weights (2009 edition), offence map, 158 neighbourhoods, H3 grid | Done: 158 neighbourhoods, 5,748 cells | `079b94e` |
| 5 | Crime incidents since 2025, each event counted once | Done: totals match the service | `6d7ac6f` |
| 6 | Scoring rules (bands, CSI rate, percentile, recency, smoothing, combine) | Done | `66ce615` |
| 7 | Score build and ranking comparison report | Done; report shared | `929afd8` |
| 8 | Live AQHI and weather alerts; environment and alert scores | Done | `820f6a6` |
| 9 | Read API: neighbourhoods, cells, sources, scoring rules | Done | `99e8355` |
| 10 | Destination score (Nominatim, coverage check, request limit) | Done: 0.7 s live | `3374fd1` |
| 11 | Route score with riskiest stretches (OSRM walking) | Done: 2.2 s live | `278312b` |
| 12 | News: CBC + GDELT, keyword labels, capped 24-hour news score | Done (GDELT blocked, see deviations) | `3bac811` |
| 13 | Web map and "How scores work" page | Done | `c1f698f` |
| 14 | README, demo warm-up script, secrets scan | Done | `c2a432c` |
| | Clean-up (code-simplifier) | Done | `4b39181` |
| r2+r3 | Foot traffic counts; street scores per person on foot; "compared with surroundings"; busy-area note; stand-out route stretches | Done | `d5fb347` |

## Additions from design revisions 2 and 3
**What was built:**
- **New source `toronto_tmc`:**
  - the City of Toronto's most recent intersection count at 6,394 locations, loaded into `foot_traffic_counts`
  - the newest count is from 2026-09-23
  - the file is looked up by name through the City's CKAN API
  - command: `python -m uavert ingest traffic`, also part of `ingest all`
- **Foot traffic per street cell:**
  - the median pedestrians per hour of 2015+ counts within 1 ring, else 2, else 3, else the city median
  - 80 of 5,748 cells have no count within about 600 m and are marked "estimated"
- **Street crime score per person:** the percentile of `smoothed_value ÷ max(foot traffic, 100)`.
- **`vs_surroundings`:** per-person value ÷ the median of the other cells within 6 rings.
- **`busy_area`:** foot traffic at or above the 90th percentile of counted locations (128 cells).
- **Reasons:** each street cell gains a foot traffic reason with the count dates used. In busy areas it reads "Busy area: ... the score allows for crowds".
- **Route stretches:** at least 1.5× their surroundings, the ones that stand out most first, at most 3. `segments_note` explains when none qualifies.
- **API additions:**
  - `foot_traffic_per_hour`, `vs_surroundings` and `busy_area` on cells, destinations and stretches
  - `foot_traffic_counts_used` and `foot_traffic_dates` on destinations
  - new parameters on `/scoring-rules`
- **Web map:** tooltips and panels show foot traffic and "× its surroundings". The route panel lists "Stretches that stand out". The rules page has a new section, "Allowing for crowds".

**Live results** (live server, 2026-10-01):

| Check | Before | After |
|---|---|---|
| City Hall street score | 100 | 84 (about 1,378 people an hour, 36 counts 2018–2025, busy area) |
| Union Station street score | 100 | 53 |
| Union Station → Kensington walk | all 8 blocks 97–100, one 2.8 km "stretch" | overall 95 (the highest block); one stretch stands out: 833 m near Kensington at 2.7× its surroundings |
| City Hall → Yonge-Dundas walk | all 100 | the Yonge-Dundas end stands out at 2.9×, plus a short stretch at 1.5× |
| Jane and Finch → York University walk | | one block at 14× its quiet surroundings (shown as "more than 10×"), and a second at 3.6× |

The overall 0–100 score of a downtown walk is still "high", as designed: it is the highest block on the route, and downtown blocks still rank high per person.

## Addendum: time of day ([01-03-time-of-day.md](01-03-time-of-day.md), approved 2026-10-01 13:21)
Built after phase 4 was approved, at the user's request, on the same branch. Steps T1–T5 of that document's plan:

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | People out by hour: `data/activity_by_hour.csv` (City counts 6 am–7 pm; Bike Share 2025 at night, scaled by 1.005), `activity_by_hour` table, `activity_profile` source | Done | `19fc200` |
| T2 | Street crime score for each of the 24 hours (3-hour window, leaning toward the city pattern, per person at that hour, ranked across all blocks and hours) | Done | `5372bc9`, fix `c684ce8` |
| T3 | Optional `hour` on cells, risk-scores and route-risks; `time` object; a reason for the hour | Done | `2aaf114` |
| T4 | "When" selector on the map; time-of-day section on the rules page | Done | `660fcb2` |
| T5 | README and this addendum | Done | this commit |

**Live results** (real data, 2026-10-01):

| Check | Result |
|---|---|
| City Hall street score | all day 84; 2 pm 87; 10 pm 94; 2 am 99 (criterion 25: 2 am > 2 pm) |
| Kensington | 77 at 2 pm → 100 at 2 am: its late-night incidents run at 1.6× its average |
| Union Station → Kensington walk | 84 at 2 pm → 100 at 2 am |
| Reason at 2 am | "At 2 am: incidents near here run at about 0.8× this block's average, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)" |

**Tests:** 142 pass, including new unit tests for:
- the time window and its wrap past midnight
- the hourly shares, with untimed incidents spread evenly
- leaning toward the city pattern
- intensity
- per person at each hour
- the build producing higher scores at an emptier hour
- the hourly profile file

And API tests for:
- "no hour means unchanged"
- scores and reasons at 2 am and 2 pm
- cells and route at an hour
- 422 for bad hours

**Deviations:**
1. **Untimed incidents** follow the design (homicides count evenly across the day), but incidents with 00:00 times are kept as midnight, as noted in the design's risks.
2. **Display fix:** while checking the map I found that whole-day dates (stored as midnight UTC) displayed as the evening before in Toronto time, for example "Dec 30, 2025, 7:00 p.m." instead of "Dec 31, 2025". This affected every source, not only the new one. Both pages now show such dates as dates.
3. **Wording for busy hours:** above the daytime average, the hour reason says "foot traffic is about 1.1× the daytime average" rather than "107% of daytime foot traffic".
4. **Process slip:** commit `5372bc9` was made while one new test was failing. My command printed only the last line of the pytest output, and the failure was in the line above. The test's second assertion was wrong, not the code. It was fixed in `c684ce8`, and since then each commit runs the suite and checks its exit code.

**Screenshots:** [03-map-with-time-selector.png](screenshots/03-map-with-time-selector.png), [04-rules-page-time.png](screenshots/04-rules-page-time.png).

**Follow-ups:**
- day of week and weekends
- night-only "stand out" stretches
- time-aware neighbourhood colours
- intersection counts at night, if the City ever publishes them

## Files changed

| File | New / changed | Summary |
|---|---|---|
| `pyproject.toml`, `.env.example`, `.gitignore`, `README.md` | New | Package and dependencies, settings template, setup/run/test guide, API summary, licences |
| `db/migrations/001_extensions.sql`, `002_core.sql` | New | PostGIS + H3; 15 tables with collection dates, region ids, unique natural keys, spatial indexes |
| `data/csi_weights.csv`, `data/offence_map.csv` | New | StatCan 2009 weights (26 offences) and 24 Toronto Police → CSI mappings, with source URL and retrieval date |
| `src/uavert/config.py`, `db.py`, `freshness.py`, `__main__.py` | New | Settings; connection pool and migration runner; shared data-date helpers; `python -m uavert` |
| `src/uavert/sources/*.py` | New | `http` (retries, `SourceUnavailable`), `arcgis` (paging), `tps`, `eccc`, `news` (RSS, GDELT, labels, place extraction), `geocode` (Nominatim, 1 request per second, 24-hour cache), `routing` (OSRM) |
| `src/uavert/ingest/*.py` | New | `cli` (migrate / ingest / build-scores / serve), `registry` (source licences), `runs` (`ingest_runs` bookkeeping), `reference`, `crime`, `live`, `news` |
| `src/uavert/scoring/*.py` | New | `bands`, `crime`, `events` (count once), `combine`, `environment`, `alerts`, `news`, `route`, `build` |
| `src/uavert/api/*.py`, `api/routes/*.py` | New | App, error shape, live conditions, locating places, request limit; endpoints for neighbourhoods, cells, risk-scores, route-risks, news-events, sources, scoring-rules |
| `src/uavert/web/index.html`, `app.js`, `style.css`, `rules.html` | New | Leaflet map, destination search, route planner, news list, "Data collected" panel, rules page; light and dark themes; phone layout |
| `scripts/compare_rankings.py`, `live_check.py`, `warm_demo.py` | New | Ranking report; in-process live checks; demo warm-up |
| `tests/**` | New | 116 tests, with fixtures saved from the real Toronto Police, ECCC and CBC responses of 2026-10-01 |
| `docs/work/.../csi-vs-demo-ranking.md`, `screenshots/*` | New | Checkpoint report; map and rules page screenshots |
| `db/migrations/003_foot_traffic.sql` | New (r3) | `foot_traffic_counts`; seven new `cell_scores` columns |
| `src/uavert/sources/toronto_open_data.py`, `src/uavert/ingest/traffic.py` | New (r3) | CKAN lookup, CSV parsing (8- and 14-hour counts → per hour), bulk load |
| `src/uavert/scoring/crime.py`, `scoring/build.py`, `scoring/route.py` | Changed (r2, r3) | Foot traffic estimate, per person, surroundings ratio, busy threshold, stand-out stretches |
| `src/uavert/api/locate.py`, `api/routes/cells.py`, `api/routes/route_risks.py`, `api/routes/sources.py` | Changed (r2, r3) | New response fields and parameters |
| `src/uavert/web/app.js`, `rules.html`, `README.md` | Changed (r2, r3) | Foot traffic and stand-out stretches in the UI; rules page section; README |
| `tests/test_foot_traffic.py`, `tests/test_route_rules.py`, `tests/fixtures/traffic/tmc_sample.csv`, other tests | New / changed (r2, r3) | 17 real rows from the City file; foot traffic, ratio, threshold and stretch tests; API field tests; a failed traffic download keeps the stored counts |

## Deviations from the plan

None of these changes a contract or an acceptance criterion unless marked.

1. **Database driver: `asyncpg` instead of `psycopg`.** Already recorded in the approved plan: Windows Smart App Control blocks psycopg's bundled library.
2. **`python -m uavert ...` instead of the `uavert` command.** Smart App Control also blocks the small `uavert.exe` launcher that the install generates. The README documents `python -m uavert`.
3. **How a sparse cell leans toward its neighbourhood.** The design gave a formula, `(n × local + 5 × hood) ÷ (n + 5)`, but also said a cell with 5 or more incidents is "mostly its own". Those two contradict each other: the formula gives only 50% at 5 incidents.
   - **What was built:** the rule as the definition words it ("a minimum number of incidents before it is scored on its own"):
     - 0 incidents → the neighbourhood average
     - 1–4 incidents → a straight-line blend
     - 5 or more → the cell's own value
   - **Tests:** a hand-worked unit test covers it.
4. **AQHI example number.** The design's test table used "AQHI 8 (score 61)" as an example. The mapping as built, with breakpoints aligned to Health Canada's bands, gives 59 for AQHI 8. That is still in the "elevated" band, as intended. The test checks the built mapping.
5. **Street grid size: 5,748 cells, not about 6,500.** Cells are assigned to the neighbourhood containing their centre, so no cell is counted twice. Toronto's 643 km² at about 0.1 km² per cell agrees with this.
6. **Neighbourhood news effect.** For a street cell, news counts within about 500 m, as designed. The design didn't say how news applies to a whole neighbourhood. As built, a report raises the neighbourhood it falls inside.
7. **Duplicate victims collapsed.** Major Crime Indicators can list the same offence once per victim. These are stored once per (event, offence): 62,227 records became 57,633 rows. Each event is then counted once at its most serious offence, as designed.
8. **Personal email removed from outgoing requests.** My first version put your email address in the app's identification header (User-Agent). That sent it to Nominatim, OSRM, CBC, GDELT, Environment Canada and Toronto Police on every request. It now sends only `uavert-demo/0.1`. This change also fixed CBC, whose servers were stalling on the longer header.
9. **GDELT returns "too many requests" (HTTP 429) from this network**, even when called once every 6 seconds. The failure is recorded (the "Data collected" panel shows it) and the other sources carry on. **In practice the news feature runs on CBC Toronto only for now.**
10. **Revisions 2 and 3: two small points.**
    - **Order of crime reasons:** the API shows at most 2 crime reasons per score. So each street score shows the top incident reason first, then the foot traffic reason. A second incident group or the "leans on the neighbourhood" note follows when there is room.
    - **Display cap:** ratios above 10 are shown on the map as "more than 10×". The API keeps the exact number.
11. **Small extras needed to finish the steps:**
    - `scripts/live_check.py`, a development check tool
    - the ArcGIS paging order is optional, because the neighbourhood layer has no `OBJECTID` field
    - the street data date is shown in Toronto time (June 30), not UTC
    - `pyflakes` was used once to check for unused imports; it was not added to the project's dependencies

## Clean-up
The `code-simplifier` pass (commit `4b39181`) made no behaviour changes. All 116 tests passed and the live checks gave the same results afterwards.
- **Duplication removed:**
  - three copies of the timestamp helper and two copies of the "source dates" query became one module, `uavert/freshness.py`
  - two copies of the distance calculation became one (`scoring/route.distance_m`)
  - two copies of lazily creating the shared HTTP client became one (`api/locate.py`)
- **Smaller tidy-ups:**
  - a one-line helper in the percentile function was inlined
  - unused imports were removed from 2 test files
  - `pyflakes` now reports nothing

## Follow-up ideas
These were not done in this task. The first three affect how the demo reads and are worth deciding on before or soon after Tuesday.

1. **The "busy street" effect: addressed by revisions 2 and 3.** What remains:
   - **Night-time:** foot traffic counts are weekday daytime snapshots, so night-time risk per person isn't measured.
   - **Neighbourhood scores** are still per resident, not per visitor.
2. **A quarter of the city is always "high".** Percentile ranking puts about 25% of street cells in each band by construction. Fixed thresholds on the weighted value would let the bands mean the same thing month to month.
3. **A single homicide in a small neighbourhood.** One homicide moves a small neighbourhood a long way (for example Bayview Woods-Steeles rises 74 places). Options: a three-year average for homicides, or wording that points out the small-number effect.
4. **Current CSI weights.** Ask Statistics Canada for the current weight table. Switching to it is a data change (`CSI_EDITION`).
5. **News accuracy and access.**
   - **Accuracy:** a language model or a reviewer to check labels and locations.
   - **Access:** a licensed news feed or CBC's permission, and a news source that doesn't rate-limit us the way GDELT does.
6. **Separate day and night street scores.** The incident times are already stored.
7. **Map links that keep their place.** Links that keep the map position, a search or a route, so a demo view can be shared.
8. **Production setup.** Scheduled refresh, hosting at a public address in a Canadian region, user accounts, CI/CD and monitoring. These are all outside this task's scope.

## What happens next
Once this is approved, phase 5 (test the work) covers revisions 2 and 3 as well. It:
- runs the full test suite and the README steps from a clean setup
- loads data into an **empty** database copy, to check acceptance criterion 1 as worded
- maps each of the 20 acceptance criteria to its evidence
- times the live checks
- reviews the full diff

The results go into `05-test-report.md`.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 13:15
- **User's response:** "yes approved i also want to add a time feature where the later in the night someone would want to selevt the time and that would also affect the safety score"
- **Revisions before approval:** 2026-10-01: added design revisions 2 and 3 (downtown fix, foot traffic) at the user's request before approval.
