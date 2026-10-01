# 4. Do the work: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval

## What this step is
This step builds the approved plan ([03-plan.md](03-plan.md)) step by step, with tests written alongside the code. It then runs a clean-up pass. This document records what was built and where it differs from the plan.

## What was done
- **All 14 plan steps** were built in order on the branch `feature/backend-foundation`. After each step the tests passed and the step was committed. A final clean-up commit followed.
- **Test suite:** `python -m pytest` reports **116 passed**.
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
10. **Small extras needed to finish the steps:**
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

1. **The "busy street" effect.** Street scores rank each block against the rest of the city.
   - **The problem:** downtown blocks have far more reported incidents because far more people are there. The whole Union Station → Kensington Market walk is "high", so the riskiest-stretch feature can't separate one downtown block from another.
   - **Options:** compare each block with its surroundings; rank within the neighbourhood; or show counts beside the score. The build plan lists these.
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
Once this is approved, phase 5 (test the work):
- runs the full test suite and the README steps from a clean setup
- loads data into an **empty** database copy, to check acceptance criterion 1 as worded
- maps each of the 20 acceptance criteria to its evidence
- times the live checks
- reviews the full diff

The results go into `05-test-report.md`.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
