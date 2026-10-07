# Uavert

Location risk scores for Toronto from public data: an ingestion pipeline, a scoring engine, a versioned API and a web map.

- **Crime:** Toronto Police incidents, weighted by Statistics Canada's Crime Severity Index (CSI), scored per neighbourhood and per street block (H3 hexagons, about 0.1 km²).
- **Foot traffic:** street scores count incidents per person on foot, using City of Toronto pedestrian counts at intersections. Walking routes highlight the stretches that stand out from their surroundings.
- **Time of day:** pick an hour and street-level scores change with it. They allow for when incidents happen nearby and how many people are out at that hour: City pedestrian counts by day, estimated from Bike Share trips at night.
- **Air quality:** live Air Quality Health Index from Environment Canada.
- **Official alerts:** Environment Canada weather alerts, scored by their own risk colour (yellow moderate, orange elevated, red high). During a heat alert, the nearest City cool space open at that time is named.
- **Crowds:** on the dates of large City events (Nuit Blanche, Pride, parades and others), nearby places are at least moderate. Major venues are mentioned as context.
- **News:** CBC Toronto and GDELT headlines about protests and violent incidents, labelled unverified.

Scores run from 0 to 100; higher means more reported risk. Crime scores compare a place with a **typical Toronto block or neighbourhood** (the median): typical = 25, and each doubling adds 20. The combined score is the highest category, never an average. No place is ever labelled "safe".

Homicides are averaged over 3 years, so a single event doesn't swing a small area. Every score rebuild also runs a **fairness check**: how closely neighbourhood scores follow household income (2021 Census). The result is shown on the "How scores work" page.

- **Hosted:** https://uavert.vercel.app (public; search engines are asked not to index it).
- **Code:** https://github.com/saikaja/uavert (private).
- **Design and decisions:** [docs/work/2026-10-01-backend-foundation/](docs/work/2026-10-01-backend-foundation/README.md).

## Requirements

- Python 3.12 or newer (developed on 3.14) and [uv](https://docs.astral.sh/uv/)
- A Neon Postgres database (Postgres 17 with the `postgis`, `h3` and `h3_postgis` extensions, which Neon supports)

## Set up

```sh
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"   # macOS/Linux: .venv/bin/python
cp .env.example .env                                            # then fill in DATABASE_URL and TEST_DATABASE_URL
```

Use the **direct** Neon host (without `-pooler`) in both URLs.

On Windows with Smart App Control, the `uavert.exe` launcher created by the install may be blocked, so run commands as `python -m uavert ...` (as below). The project uses the `asyncpg` driver because Smart App Control blocks `psycopg`'s bundled library.

## Load data and run

Every command below is run with the virtual environment's Python (`.venv/Scripts/python.exe` on Windows):

```sh
python -m uavert migrate              # create or upgrade the database schema
python -m uavert ingest all           # reference data, crime incidents, foot traffic, air quality, alerts, news (about 1 minute)
python -m uavert build-scores         # compute neighbourhood and street crime scores (about 10 seconds)
python -m uavert serve                # web map at http://localhost:8000, API docs at http://localhost:8000/api/docs
```

Two reference files are built by scripts and only need re-running when you want newer data:
- **`data/activity_by_hour.csv`** (people out by hour): built from about 315 MB of City files by `python scripts/build_activity_profile.py`.
- **`data/neighbourhood_income_2021.csv`** (census income, for the fairness check): built by `python scripts/build_neighbourhood_income.py`.

**Keeping data fresh:**
- **Locally:** `serve` refreshes air quality, alerts and news every 30 minutes (`--refresh-minutes 0` turns this off). You can also refresh by hand with `python -m uavert ingest live`.
- **Hosted:** the GitHub Actions workflow `.github/workflows/refresh.yml` refreshes the live sources hourly. Daily at 10:00 UTC it runs `ingest daily` (crime, traffic, cool spaces, large City events) and rebuilds the scores. It uses the repository secret `DATABASE_URL`. Until the app is merged into `main`, the repository variable `DATA_BRANCH` names the branch whose code it runs.

Address and route lookups are saved in the database (addresses for 30 days, routes for 7), so restarts and new hosted instances reuse them.

Each source is collected separately. If one fails, the others still run, earlier data is kept, and the command ends with a non-zero exit code. Every row records when it was collected (`collected_at`), separately from the date the data itself refers to. `ingest_runs` keeps the history of every collection.

## Hosting (Vercel)

Vercel runs the FastAPI app from `index.py`, as one function in region `cle1`, next to the Neon database in Ohio.
- **Production settings:** `DATABASE_URL` (direct Neon host) and `DB_POOL_MAX=2`.
- **Deploy by hand:** `vercel deploy --prod`.
- **Deploy from Git:** the project is connected to the GitHub repository. `main` carries a `vercel.json` that turns off Git deploys from `main` until the app is merged there. At the merge, keep the branch's `vercel.json`, and pushes to `main` will then deploy to production.
- **Refresh:** Vercel's free plan only allows scheduled jobs once a day, so the hosted data refresh runs on GitHub Actions instead (see above).

### Before a demo

```sh
python -m uavert ingest live
python -m uavert serve
python scripts/warm_demo.py           # in a second terminal: wakes the database and caches the demo addresses and routes
```

## Test

```sh
python -m pytest
```

- **Unit tests** need nothing external.
- **Tests marked `db`** use the Neon branch in `TEST_DATABASE_URL`, which they reset and seed with a small made-up dataset. Never point it at the main branch.
- **Outside services:** tests never call them; they are faked.

## API (v1)

All endpoints are read-only `GET`s and are public for now.

- **Success:** `{"data": ..., "meta": {"generated_at", "sources": {key: {"as_of", "collected_at"}}}}`
- **Errors:** `{"error": {"code", "message", "details"}}`

| Endpoint | What it returns |
|---|---|
| `/api/v1/health` | Whether the database is reachable |
| `/api/v1/neighbourhoods` | All 158 neighbourhoods with scores (GeoJSON) |
| `/api/v1/neighbourhoods/{id}` | One neighbourhood: score, reasons, crime details |
| `/api/v1/cells?bbox=minLon,minLat,maxLon,maxLat` | Street-level cells in an area of up to 25 km² (GeoJSON) |
| `/api/v1/risk-scores?address=...` or `?lat=&lon=` | Where I'm going: street and neighbourhood scores |
| `/api/v1/route-risks?from=...&to=...` | Where I'm walking: route score and up to 3 stretches that stand out from their surroundings (walks of up to 10 km) |
| `/api/v1/news-events?since_hours=24` | Recent labelled news reports |
| `/api/v1/sources` | Every source with licence, attribution, data date and collection time |
| `/api/v1/scoring-rules` | Bands, CSI weights, offence mapping, parameters, hourly activity, latest fairness check |

`/cells`, `/risk-scores` and `/route-risks` also take an optional `hour` (0–23, Toronto time). Without it, scores are for the whole day.

Address and route lookups are limited to 30 requests per minute per IP.

## Layout

```
db/migrations/            numbered SQL files, applied in order by `uavert migrate`
data/                     CSI weights, offence mapping, people out by hour, census income (CSV, each with source and retrieval date)
index.py, vercel.json     Vercel entry point and settings
.github/workflows/        scheduled data refresh for the hosted site
src/uavert/sources/       clients for outside services (Toronto Police, ECCC, news, geocoding, routing)
src/uavert/ingest/        collection runs and the command line
src/uavert/scoring/       scoring rules as pure functions, plus the score build
src/uavert/api/           FastAPI app, routes, live conditions, errors, request limit
src/uavert/web/           the web map and the "How scores work" page
scripts/                  ranking comparison report, live checks, demo warm-up
tests/                    unit tests; tests/api are API tests against the Neon test branch
```

## Data sources and licences

| Source | Licence / terms |
|---|---|
| Toronto Police Service Public Safety Data Portal | Toronto Police open data terms; data is preliminary, locations offset to the nearest intersection |
| Statistics Canada, Crime Severity Index weights (2009 published table) | Statistics Canada Open Licence |
| City of Toronto intersection traffic counts | Open Government Licence – Toronto (the dataset page says "not specified"; confirm before public launch) |
| Environment and Climate Change Canada (MSC GeoMet) | ECCC Data Servers End-use Licence |
| CBC News Toronto RSS | Personal, non-commercial use. Headlines and links only; needs permission or a licensed feed before public launch |
| Bike Share Toronto ridership 2025 (hourly pattern at night) | Open Government Licence – Toronto |
| City of Toronto Neighbourhood Profiles, 2021 Census (income, for the fairness check) | Open Government Licence – Toronto; source data Statistics Canada |
| City of Toronto Heat Relief Network (cool spaces) | Open Government Licence – Toronto (confirm before public launch) |
| City of Toronto Festivals & Events calendar (large events only) | Open Government Licence – Toronto (the dataset page says "not specified"; confirm before public launch) |
| Venue capacities | Wikipedia (CC BY-SA), cited per venue in `data/major_venues.csv` |
| The GDELT Project | Free with attribution |
| OpenStreetMap (Nominatim geocoding, OSRM walking routes, map tiles) | ODbL; each service's fair-use policy applies |
