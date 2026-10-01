# Uavert

Location risk scores for Toronto from public data: an ingestion pipeline, a scoring engine, a versioned API and a web map.

- **Crime:** Toronto Police incidents, weighted by Statistics Canada's Crime Severity Index (CSI), scored per neighbourhood and per street block (H3 hexagons, about 0.1 km²).
- **Foot traffic:** street scores count incidents per person on foot, using City of Toronto pedestrian counts at intersections. Walking routes highlight the stretches that stand out from their surroundings.
- **Time of day:** pick an hour and street-level scores change with it. They allow for when incidents happen nearby and how many people are out at that hour: City pedestrian counts by day, estimated from Bike Share trips at night.
- **Air quality:** live Air Quality Health Index from Environment Canada.
- **Official alerts:** Environment Canada weather alerts.
- **News:** CBC Toronto and GDELT headlines about protests and violent incidents, labelled unverified.

Scores run from 0 to 100; higher means more reported risk. The combined score is the highest category, never an average. No place is ever labelled "safe".

Design and decisions: [docs/work/2026-10-01-backend-foundation/](docs/work/2026-10-01-backend-foundation/README.md).

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

`data/activity_by_hour.csv` (people out by hour) is built from about 315 MB of City files by `python scripts/build_activity_profile.py`. It only needs re-running when you want newer data.

Refresh only the live parts (air quality, alerts, news) with `python -m uavert ingest live`. Crime data changes only when Toronto Police publishes an update; rerun `ingest crime` and then `build-scores`.

Each source is collected separately. If one fails, the others still run, earlier data is kept, and the command ends with a non-zero exit code. Every row records when it was collected (`collected_at`), separately from the date the data itself refers to. `ingest_runs` keeps the history of every collection.

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
| `/api/v1/scoring-rules` | Bands, CSI weights, offence mapping, parameters |

`/cells`, `/risk-scores` and `/route-risks` also take an optional `hour` (0–23, Toronto time). Without it, scores are for the whole day.

Address and route lookups are limited to 30 requests per minute per IP.

## Layout

```
db/migrations/            numbered SQL files, applied in order by `uavert migrate`
data/                     CSI weights, offence mapping, people out by hour (CSV, each with source and retrieval date)
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
| The GDELT Project | Free with attribution |
| OpenStreetMap (Nominatim geocoding, OSRM walking routes, map tiles) | ODbL; each service's fair-use policy applies |
