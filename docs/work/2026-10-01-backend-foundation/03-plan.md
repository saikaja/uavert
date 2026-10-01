# 3. Start the work: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval

## What this step is
This step does two things before any code is written:
1. **Sets up a working base:** the repository, the database and the dependencies.
2. **Breaks the approved design into small ordered steps.** Each step keeps the tests passing.

## What was done
- Created the Git repository and committed the task documents.
- Created a work branch.
- Created the Neon project, installed the extensions, and made a separate `test` copy of the database for the automated tests.
- Installed and checked every Python dependency on this PC.
- Found two facts about this PC that change small details of the design:
  1. **This PC has an ARM processor and runs Windows Smart App Control (an app-security setting).**
     - Python 3.14 here is the standard x64 build, running under emulation.
     - Windows blocked the library file bundled with `psycopg`, the Postgres driver named in the design (`DLL load failed ... An Application Control policy has blocked this file`).
     - Two other drivers loaded without problems: `asyncpg` (compiled) and `pg8000` (pure Python).
     - **Change from the design:** use `asyncpg` instead of `psycopg`. It is fast, it has built-in bulk loading (`copy_records_to_table`, which replaces COPY in the design), and it suits FastAPI.
     - If Windows later blocks `asyncpg` too, `pg8000` is the fallback.
     - This changes no behaviour, contract or acceptance criterion.
  2. **Neon has no Canadian region.** The available regions are in the US, Europe, Asia-Pacific and South America. The project was created in **AWS US East 2 (Ohio)**, the closest to Toronto. As agreed, this is acceptable while the database holds only public data.
- All other dependencies installed and loaded on Python 3.14, so the planned fallback to 3.12 is not needed: fastapi, uvicorn, pydantic-settings, httpx, h3, shapely, pytest and respx.

## Workspace
- **Repository / branch:**
  - `C:\Users\saika\uavert`, new Git repository
  - `main` holds the commit "Add task docs for backend foundation (phases 1-2)" (`e74ac0f`)
  - work happens on **`feature/backend-foundation`**
- **Database:**
  - Neon project `uavert` (`frosty-salad-15901431`): Postgres 17.11, region `aws-us-east-2`
  - branch `main` (`br-square-river-b5cbk61i`) for real data
  - branch `test` (`br-withered-resonance-b5lh1th7`) for automated tests
  - extensions installed on both branches: `postgis` 3.5.7, `postgis_raster` 3.5.7, `h3` 4.1.3, `h3_postgis` 4.1.3
  - connection strings are in `.env` (`DATABASE_URL`, `TEST_DATABASE_URL`), which `git check-ignore` confirms is ignored
  - Neon's weekly maintenance window is **Tuesday 08:00–09:00 UTC (4–5 AM Toronto time)**, well before the demo
- **Dependencies installed:** virtual environment `.venv` (Python 3.14.7, x64), managed with `uv` 0.12.18. Every package imported successfully:
  - fastapi, uvicorn[standard], asyncpg, pg8000 (fallback), pydantic-settings, httpx, h3, shapely
  - for tests: pytest 9.1.1, respx
- **Baseline:**
  - `asyncpg` connection to Neon → OK
  - `select h3_lat_lng_to_cell(point(-79.3840,43.6536), 9)` → `892b9bc46d7ffff` (the H3 extension works; note that points are given as longitude then latitude)
  - There are no tests yet, so `pytest` has nothing to run. The baseline is an empty project, with no existing failures to confuse with new ones.

## Implementation plan
Order: risky parts first (data loading, CSI scoring), then the features in the agreed build order, so each finished step can be demoed. After each step:
- the tests pass
- the work is committed to `feature/backend-foundation`

Target days are a guide for the Tuesday, October 6 demo.

| # | What | Files | Tests | Done when |
|---|---|---|---|---|
| 1 | Project skeleton: package, settings, database pool, migration runner, `uavert` command, health endpoint | `pyproject.toml`, `.env.example`, `src/uavert/{config,db}.py`, `src/uavert/ingest/cli.py`, `src/uavert/api/app.py`, `tests/conftest.py` | Settings load from the environment; `migrate` run twice changes nothing; `GET /api/v1/health` returns 200 on the test branch | `pytest` passes; `uavert migrate` runs on `test`. *Thu* |
| 2 | Database schema, with `collected_at` on every data table and the `ingest_runs` history | `db/migrations/001_extensions.sql`, `002_core.sql` | Every data table has `collected_at`; the unique keys exist | Migrations applied to `test` and `main`. *Thu* |
| 3 | Shared HTTP client (timeouts, retries, `SourceUnavailable`), ArcGIS paging, Toronto Police parsers | `src/uavert/sources/{http,arcgis,tps}.py`, `tests/fixtures/tps/*.json` (small saved samples of real responses) | Paging across 2,000-row pages; date conversion (epoch milliseconds → UTC); missing locations; a timeout becomes `SourceUnavailable` | Parsers pass on the saved samples. *Thu* |
| 4 | Reference data: CSI weights (2009 edition, with source URL and retrieval date), offence map, 158 neighbourhoods with 2025 counts and population, the H3 cell grid, the `sources` list | `data/csi_weights.csv`, `data/offence_map.csv`, `src/uavert/ingest/reference.py` | An offence with no mapping stops with a clear error naming it; a re-run adds no duplicates; every row has `collected_at` | On `main`: 158 neighbourhoods and about 6,500 cells. *Thu* |
| 5 | Crime incidents: Major Crime Indicators, shootings and homicides from 2025-01-01 to the latest date, each event counted once (homicide over shooting over other offences), H3 cell assigned, loaded in bulk | `src/uavert/ingest/crime.py` | Duplicate removal on made-up overlapping records; a re-run keeps counts the same; incidents with no location are kept but get no cell | Row counts on `main` match the ArcGIS totals minus removed duplicates (written in the step notes). *Thu–Fri* |
| 6 | Scoring core as pure functions: bands, percentile rank, CSI weighting, recency, nearby-cell smoothing, leaning toward the neighbourhood, highest-score combination, reasons | `src/uavert/scoring/{bands,crime,combine}.py` | Hand-worked tests for criteria 5, 6 and 7; a band test for criterion 9 (no "safe") | Unit tests pass. *Fri* |
| 7 | Score build: neighbourhood and cell scores written to the database with `computed_at`; **ranking comparison report** (demo weights vs CSI) for you to review | `src/uavert/scoring/build.py`, `docs/work/.../csi-vs-demo-ranking.md` | The build on fixture data gives the expected scores | `uavert build-scores` runs on `main`; report written. **Checkpoint: I send you the report.** *Fri* |
| 8 | Live conditions: AQHI and weather alerts ingestion; environment and alert scores (only warnings and orange/red alerts override to "high") | `src/uavert/sources/eccc.py`, `src/uavert/ingest/live.py`, `src/uavert/scoring/{environment,alerts}.py`, `tests/fixtures/eccc/*.json` | Saved samples, including an empty alert list; AQHI → score mapping; a warning gives "high" and an advisory gives a floor of 25 (criterion 8); a failed fetch keeps old rows and records `failed` (criterion 17) | `uavert ingest live` stores current Toronto AQHI. *Fri* |
| 9 | Read API: neighbourhoods, one neighbourhood, cells by bbox, sources, scoring rules; standard response and error shapes; `meta.sources` with `as_of` and `collected_at` | `src/uavert/api/{schemas,errors}.py`, `src/uavert/api/routes/{neighbourhoods,cells,sources,rules}.py`, `tests/api/*` | API tests on the `test` branch with fixture data, covering criteria 4, 10, 11 and 9 (searching every response for "safe") | API tests pass; live `/api/v1/neighbourhoods` returns 158. *Fri* |
| 10 | Destination: Nominatim client (limited to Toronto, 1 request per second, 24-hour cache), Toronto boundary check, `GET /api/v1/risk-scores`, request limit | `src/uavert/sources/geocode.py`, `src/uavert/api/routes/risk_scores.py`, `src/uavert/api/ratelimit.py` | Faked geocoder: success, not found (404), outside Toronto (422), upstream down (502), criterion 14 | Live check of `100 Queen St W, Toronto` in under 2 s. *Sat/Mon* |
| 11 | Route: OSRM client, points every 25 m along the line → cells → riskiest stretches, `GET /api/v1/route-risks` | `src/uavert/sources/routing.py`, `src/uavert/scoring/route.py`, `src/uavert/api/routes/route_risks.py` | Stretch finding on a made-up line; route too long (422), no route (422), faked OSRM, criterion 13 | Live check of Union Station → Kensington Market in under 3 s. *Sat/Mon* |
| 12 | News: CBC RSS + GDELT clients, keyword classifier with negative keywords, place extraction + geocoding, news ingestion, news score (cap and 24-hour expiry), `GET /api/v1/news-events` | `src/uavert/sources/news.py`, `src/uavert/ingest/news.py`, `src/uavert/scoring/news.py`, `src/uavert/api/routes/news.py`, `tests/fixtures/news/*` | About 20 real headlines with expected labels, including "Torontonians don't feel safe…" which must **not** be flagged; news score at 0, 12 and 24 h; never above elevated on its own (criteria 15 and 16) | `uavert ingest news` stores today's items; the list is checked by hand. *Mon* |
| 13 | Web map: neighbourhood layer, street layer when zoomed in, details panel with reasons and dates, destination search, route planner with riskiest stretches, news list, "Data collected" panel, "How scores work" page | `src/uavert/web/{index.html,app.js,style.css,rules.html}` | Run by hand (criterion 19), with screenshots saved to the task folder | Every map feature works against the live API. *Mon* |
| 14 | Finish: README (set up, ingest, run, test), `.env.example`, secrets scan, full fresh load on `main`, timing checks, cache warm-up script for the demo addresses and routes | `README.md`, `scripts/warm_demo.py` | Full test suite (criterion 20); secrets scan (criterion 18) | The README steps work as written; ready for phase 5. *Mon* |

**If time runs short:** as agreed, web-map polish (step 13) is cut first, then news accuracy (step 12). The steps up to 11 cover the core demo:
- CSI scores
- street level
- destination and route scores

## What happens next
Once this plan is approved, phase 4 (do the work) builds the steps in order, with tests written alongside the code. At the end it records what was built in `04-implementation.md` for your approval.

After step 7 I'll send you the ranking comparison (demo weights vs CSI), so you can see how the official weights change the map before Tuesday.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
