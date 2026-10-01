# 2. Review the design: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved

## What this step is
This step chooses *how* to build what [01-definition.md](01-definition.md) agreed. It also catches problems while they are still cheap to fix. No code is written until this design and the plan in phase 3 are approved.

## What was done
- Started from the approved definition. There is no existing code, so there are no conventions to follow yet. This design sets them.
- **Checked every external source with live requests on 2026-10-01**, rather than assuming how each one works:
  - **Toronto Police ArcGIS services.** All four exist:
    - Major Crime Indicators (`Major_Crime_Indicators_Open_Data`)
    - Shootings (`Shooting_and_Firearm_Discharges_Open_Data`)
    - Homicides (`Homicides_Open_Data_ASR_RC_TBL_002`)
    - Neighbourhood Crime Rates (`Neighbourhood_Crime_Rates_Open_Data`)

    Each returns at most 2,000 rows per request, so loading pages through the results.

    Findings:
    - Each Major Crime Indicators incident carries a **UCR offence code**: the national police offence code that the Crime Severity Index (CSI) itself is built on. This lets us match offences to CSI weights by code, not by guessing from names.
    - It also has `PREMISES_TYPE`, with seven values: Outside, Commercial, Transit, Apartment, House, Educational, Other.
    - Data runs to 2026-06-30. The last 12 months contain about 41,000 incidents.
  - **The same event can appear in more than one dataset.** Between 2025-07-01 and 2026-06-30:
    - 204 of the 242 shooting records also appear in Major Crime Indicators as firearm offences
    - 18 of the 44 homicides also appear in the shootings data

    Without handling this, those events would be counted twice. The design removes duplicates by event ID.
  - **462 incidents in the last 12 months have no location.** They are counted at neighbourhood level but cannot be placed on the street map.
  - **Statistics Canada CSI weights.**
    - The only per-offence weight table StatCan publishes openly is the 2009 table in *Measuring Crime in Canada*: 27 offences, including murder 7,042, discharging a firearm with intent 988, robbery 583, aggravated assault (level 3) 405, break and enter 187, theft over $5,000 139, theft of a motor vehicle 84, assault with a weapon (level 2) 77, and assault (level 1) 23.
    - StatCan updates the weights every five years, but I could not find a newer full table published.
  - **ECCC AQHI.** `api.weather.gc.ca/collections/aqhi-observations-realtime` returns current readings for Toronto's stations (for example Toronto West 2.51 and Toronto North 2.62 at 11:00 EDT today).
  - **ECCC weather alerts.** `api.weather.gc.ca/collections/weather-alerts` returns alert polygons. Each alert carries:
    - `alert_type`: advisory, watch, warning or statement
    - `risk_colour`: yellow, orange or red
    - `status`

    No alerts are active for Toronto today.
  - **Walking routes.** The OSRM walking server at `routing.openstreetmap.de` returned Union Station → Kensington Market (2.5 km), with no key needed.
  - **Address search.** Nominatim geocodes "100 Queen St W, Toronto" (Toronto City Hall), with no key needed.
  - **News.** I tested two sources:
    - **GDELT** returned off-topic results: a Chinese-language article and a BC news roundup. It only returns headlines, and allows one request every 5 seconds.
    - **The CBC Toronto RSS feed** returned 20 Toronto stories with headlines, summaries and times.

    CBC Toronto becomes the main news source and GDELT a filtered extra (see Alternatives).
  - **Neon** supports the `postgis`, `h3` and `h3_postgis` extensions.
- **Applied the `api-design` skill.** It changed four things:
  - all paths live under `/api/v1/`, with plural kebab-case nouns
  - responses share one shape: `{ "data": ..., "meta": ... }`
  - errors share one shape: `{ "error": { "code", "message", "details" } }`
  - the endpoints that call outside services (address and route) get request limits and caching

  The endpoint names in the definition (for example `/v1/score`) are renamed to match, without changing what they do. See Contracts.

## Approach

### Overview
A single Python package with three entry points:
1. **Ingestion command line** (`uavert ingest ...`): pulls each source, cleans it and writes it to Neon.
2. **Scoring engine:** pure Python functions, with no database or network access, so every rule can be unit-tested. A score build step runs it over the database and stores crime scores per neighbourhood and per street cell.
3. **FastAPI app:** serves `/api/v1/*` and the web map, from the same process.

### How the data flows

```
Toronto Police, StatCan CSI, ECCC AQHI and alerts, CBC/GDELT news
        │  ingestion (one command per source; each run is recorded and repeatable)
        ▼
Neon Postgres + PostGIS + H3
  incidents ─┐
  neighbourhoods ─┼──► score build ──► neighbourhood_scores, cell_scores
  csi_weights, offence_map ─┘           (crime part, computed in advance)
  aqhi_readings, official_alerts, news_events  (live parts)
        │
        ▼
API request: crime score from the database (computed in advance)
           + live AQHI, alert and news scores
           → combined score, band, reasons
        ▼
Web map (Leaflet), API docs page
```

Crime scores change only when crime data is reloaded, so they are computed in advance. The live parts (air quality, alerts, news) are combined at request time, which takes milliseconds because each is a small table. This split is what scales:
- for a larger area, the slow part is a batch job
- requests stay cheap

### CSI weights and offence mapping
- **Weights.**
  - Stored in `data/csi_weights.csv` (offence, weight, edition `2009`, source URL), loaded into `csi_weights`.
  - The edition column means that a newer StatCan table, once we get one, becomes a new edition. Scores then switch to it with a config change and no code change.
- **Offence mapping.**
  - Stored in `data/offence_map.csv` and loaded into `offence_map`.
  - Each Toronto Police offence (UCR code + extension) maps to one CSI offence, marked `exact` or `closest`.
  - Ingestion stops with an error naming any offence that has no mapping (acceptance criterion 2).

The full mapping for the offences seen in the last 12 months:

| Toronto Police offence (UCR) | CSI offence | Weight | Match |
|---|---|---|---|
| Homicide (Homicides dataset) | Murder, 1st and 2nd degree | 7,042 | closest: the data doesn't separate murder from manslaughter (1,822) |
| Discharge Firearm With Intent (1450-120) | Discharging firearm with intent | 988 | exact |
| Shooting or firearm discharge, only in the Shootings dataset | Discharging firearm with intent | 988 | closest |
| Discharge Firearm - Recklessly (1450-100) | Discharging firearm with intent | 988 | closest: no separate weight published |
| Robbery, all kinds (1610) | Robbery | 583 | exact |
| Aggravated Assault, including peace officer (1410, 1462) | Assault, level 3 | 405 | exact |
| Use Firearm in Commission of Offence (1455) | Using firearm in commission of an offence | 267 | exact |
| B&E, all kinds (2120, 2121) | Breaking and entering | 187 | exact |
| Theft Over, all kinds (2130, 2132, 2133) | Theft over $5,000 | 139 | exact |
| Pointing a Firearm (1457) | Weapons possession | 88 | closest |
| Theft of Motor Vehicle (2135) | Theft of a motor vehicle | 84 | exact |
| Assault With Weapon / Bodily Harm (1420) | Assault, level 2 | 77 | exact |
| Assault Peace Officer With Weapon / Bodily Harm (1461) | Assault, level 2 | 77 | closest |
| Unlawfully Causing Bodily Harm; Criminal Negligence Causing Bodily Harm (1440, 1470) | Assault, level 2 | 77 | closest |
| Assault (1430) | Assault, level 1 | 23 | exact |
| Assault Peace Officer, Disarming an Officer, other assaults (1460, 1480) | Assault, level 1 | 23 | closest |
| Theft from vehicle under $5,000; bicycle theft (neighbourhood table only) | Theft under $5,000 | 37 | exact |

### Neighbourhood crime score
Calendar year 2025, matching the population figures and the existing demo:

```
weighted_rate = Σ (2025 incidents of each offence × CSI weight) ÷ population_2025 × 100,000
crime_score   = percentile rank of weighted_rate among the 158 neighbourhoods (0–100)
```

- Incidents come from the incident datasets, with duplicates removed and grouped by `HOOD_158`. This uses the exact offence codes rather than broad categories.
- Theft from vehicles and bicycle theft are not in the incident datasets, so their 2025 counts come from the neighbourhood table.
- All crime types count here, including incidents inside homes: this is the overall picture of the neighbourhood.

### Street-cell crime score
Last 12 months of data, ending at the newest incident date:
1. **Cells.**
   - Toronto is divided into H3 resolution-9 hexagons, each about 0.1 km² with sides of about 175 m: roughly 6,500 cells.
   - Each cell is assigned to the neighbourhood that contains its centre.
2. **Which incidents count:** only those with `PREMISES_TYPE` of Outside, Transit or Commercial, plus all shootings and homicides (those datasets don't record premises). Apartment, House, Educational and Other are left out.
3. **Recency:** each incident is weighted by `0.5 ^ (age_in_days / 180)`, so an incident six months old counts half.
4. **Cell value:** `own = Σ (CSI weight × recency)` over the cell's incidents.
5. **Short walking distance:** `local = own + 0.5 × average(own of the 6 neighbouring cells)`. This reflects what happens within about 250 m, as the plan describes.
6. **Too few incidents:**
   - If a cell and its neighbours have fewer than `MIN_INCIDENTS = 5` incidents, it leans toward its neighbourhood: `smoothed = (n × local + 5 × hood_avg_local) ÷ (n + 5)`, where `hood_avg_local` is the average `local` of the neighbourhood's cells.
   - With 0 incidents the cell takes its neighbourhood's average. With 5 or more it is mostly its own.
7. **Score:** `crime_score` is the percentile rank of `smoothed` among all Toronto cells.

Each cell also stores:
- its incident count
- a count by offence group
- its top 3 contributing offences

So reasons can say, for example, "4 street robberies within about 250 m in the last 12 months".

### Environment score (AQHI)
- Each area uses the **nearest** reporting AQHI station, measured from its centre. Toronto has about 4 stations.
- AQHI maps onto the same 0–100 bands, scaling evenly within each band:

| AQHI | Health Canada risk | Score range | Band |
|---|---|---|---|
| 1–3 | Low | 0–24 | lower |
| 4–6 | Moderate | 25–49 | moderate |
| 7–10 | High | 50–74 | elevated |
| above 10 | Very high | 75–100 | high |

- A reading more than 3 hours old is still used. Its age is shown, and the reason is marked "not current".

### Official alerts (decision for you)
ECCC sends many minor alerts (fog, frost, special weather statements). If every one of them put the whole city in "high", the map would often be red for fog, which would hurt credibility. Proposed rule:

- **Warnings**, and any alert with `risk_colour` orange or red: the area goes to the **high** band (score at least 90). This matches the definition's "an active official alert moves the area to the top band", reading "official alert" as an ECCC warning.
- **Watches and advisories:** score at least 25 (moderate). They appear in reasons, but don't override.
- **Statements:** shown in reasons only.
- **Which areas:** those whose centre falls inside the alert polygon.

### News and protest signals
**Sources:**
1. **CBC Toronto RSS** (main source): headline, summary, link and time.
2. **GDELT** (extra): `sourcecountry=Canada`, English only, at most one request every 6 seconds.

We store the headline, link, source and time only, never the article text.

**Classifying a story:** keyword lists, matched on headline + summary:
- **Protest:** protest, demonstration, rally, march, blockade, encampment clearing.
- **Violent incident:** shooting, shot, stabbing, stabbed, homicide, murder, assault, robbery, carjacking, swarming, gunfire.
- **Negative keywords** cut false matches: for example "feel safe", "mayoral race", "trial", "sentenced", "anniversary". A story about a court case is not a new incident.
- Stories older than 24 hours are dropped.

**Locating a story:**
1. **Intersection patterns** such as "Queen Street West and Spadina Avenue" or "Jane and Finch area".
2. **Toronto neighbourhood names:** any of the 158 names in the text.

Matches are geocoded with Nominatim, limited to Toronto. No match means the story is `citywide`: it is listed for information only and changes no score.

**Effect on scores:**
- `news_score = cap × (1 − hours_since_published ÷ 24)` for the story's cell and the cells up to 2 rings around it (about 500 m)
- `cap = 74` (top of "elevated") for violent incidents, `60` for protests
- if several stories overlap, the highest wins
- reasons show "Unverified news report: <headline> (CBC News, 2 h ago)" with a link

### Combined score and reasons
- `combined = max(crime, environment, alert, news)`, the same rule for a neighbourhood, a cell, a destination and a route.
- **Bands:** 0–24 `lower`, 25–49 `moderate`, 50–74 `elevated`, 75–100 `high`. One shared function defines these, and a test checks that the word "safe" never appears in any API response.
- **Reasons:** each category produces up to 2 reasons, each with:
  - a `value`
  - a short `text`
  - a `source_key`
  - the date of the data behind it (`as_of`)

  The top 3 overall are returned, highest category score first.

### Destination
Steps:
1. Geocode the address with Nominatim, limited to Toronto.
2. Reject a result outside the Toronto boundary (the union of the 158 neighbourhoods).
3. Find its H3 cell and its neighbourhood.
4. Return both scores.

### Route
Steps:
1. Geocode the start and end (or take latitude/longitude directly).
2. Get the walking route from OSRM (`routed-foot`).
3. Add points along the line every 25 m and convert each to its H3 cell, keeping the order.
4. Look up each cell's combined score.
5. **Route score** = the highest cell score.
6. **Riskiest stretches:** runs of consecutive cells in the same band, ranked by score; the top 3 are returned, each with its line, score and reasons.

Limits:
- at most 10 km of walking; longer routes get a clear 422 error
- the route must stay inside Toronto

### Handling failures
- **Ingestion runs.** Every run of a source writes one row to `ingest_runs`: start time, end time, `ok` or `failed`, row count and error message.
  - A failed source keeps its last stored data.
  - The command keeps going with the other sources and ends with a summary and a non-zero exit code.
- **Network calls.** Each outside call has:
  - a 10-second timeout
  - 2 retries with backoff
  - a clear exception type (`SourceUnavailable`)
- **API at request time:**
  - if geocoding or routing fails, the API returns **502 `upstream_unavailable`** with a readable message
  - the stored scores still serve

### Collection dates (added at approval, at the user's request)
Every piece of information records when we collected it, separately from the date the information itself refers to:
- **Every stored row** gets a `collected_at` timestamp (when our ingestion fetched it), next to its own date:
  - `occurred_at` for incidents
  - `observed_at` for AQHI
  - `issued_at` for alerts
  - `published_at` for news
  - `valid_year` for the 2025 rates
  - `edition` for CSI weights

  Updated rows keep their first `collected_at` and also get `last_seen_at`.
- **`ingest_runs`** keeps a permanent history of every collection: source, start, end, status and row count. It is never overwritten, so we can always answer "what did we have on date X".
- **Computed scores** store `computed_at` and the `collected_at` of each source they used.
- **API:**
  - every response's `meta.sources` lists each source's data date (`as_of`) and collection time (`collected_at`)
  - every reason carries both dates as well
- **Web map:** a "Data collected" panel lists each source with "data up to <date>, collected <date/time>". The details panel shows the dates for each reason.
- **Reference data:** files checked into `data/` (CSI weights, offence map) record their source URL and the date we retrieved them, in a header row.

### Configuration and secrets
- Settings come from environment variables, read with `pydantic-settings`: `DATABASE_URL`, `NOMINATIM_USER_AGENT`, `OSRM_URL`, `CSI_EDITION`, and so on.
- `.env` is git-ignored and `.env.example` is committed.
- No keys are needed for any source in this task.

### Scale path
This design doesn't build these items; it doesn't block any of them.
- **New cities:**
  - `region_id` is on every place-based table
  - each city's police data gets its own small loader that writes the same `incidents` table
  - the scoring code doesn't change
- **Global:** H3 works worldwide, and `csi_weights` and `offence_map` are per country and per source.
- **Load:**
  - the API holds no state between requests, so it can run as several copies on Cloud Run or ECS
  - crime scores are precomputed
  - add a cache such as Redis for geocoding and routing when needed
- **Data refresh:** the ingest commands are already separate jobs, which a scheduler such as Cloud Scheduler or cron can run later.
- **Users and Canada region:** user tables will go in a new database in a Canadian region; the public risk data can stay where it is or be copied there.
- **Database changes:** numbered SQL migration files, applied in order and recorded in a `schema_migrations` table.

## Changes
All files are new; the repository is empty.

| File | New / changed | What changes |
|---|---|---|
| `pyproject.toml` | New | Package `uavert`, Python ≥ 3.12. Dependencies: fastapi, uvicorn, psycopg[binary,pool], pydantic-settings, httpx, h3, shapely; dev: pytest, respx. Script `uavert` |
| `.gitignore`, `.env.example`, `README.md` | New | Ignore `.env` and virtual environments; list the settings; setup, ingest, run and test steps |
| `db/migrations/001_extensions.sql` | New | `postgis`, `h3`, `h3_postgis` |
| `db/migrations/002_core.sql` | New | Tables: `regions`, `sources`, `ingest_runs`, `neighbourhoods`, `csi_weights`, `offence_map`, `incidents`, `cells`, `neighbourhood_scores`, `cell_scores`, `aqhi_readings`, `official_alerts`, `news_events`, plus their indexes (GiST on geometry, B-tree on h3, unique natural keys) |
| `data/csi_weights.csv`, `data/offence_map.csv` | New | The tables above, so they can be reviewed |
| `src/uavert/config.py` | New | Settings |
| `src/uavert/db.py` | New | Connection pool, migration runner |
| `src/uavert/sources/arcgis.py` | New | Paged ArcGIS queries: 2,000 rows per page, request coordinates in WGS84 (`outSR=4326`) |
| `src/uavert/sources/tps.py` | New | The four Toronto Police datasets, parsed into clean records |
| `src/uavert/sources/eccc.py` | New | AQHI readings and weather alerts |
| `src/uavert/sources/news.py` | New | CBC RSS + GDELT clients, keyword classifier, place extraction |
| `src/uavert/sources/geocode.py` | New | Nominatim client: limited to Toronto, 1 request per second, cached |
| `src/uavert/sources/routing.py` | New | OSRM walking-route client |
| `src/uavert/sources/http.py` | New | Shared httpx client: timeouts, retries, `SourceUnavailable` |
| `src/uavert/ingest/cli.py` | New | `uavert migrate`, `uavert ingest {reference,crime,aqhi,alerts,news,live,all}`, `uavert build-scores` |
| `src/uavert/ingest/*.py` | New | One module per source: insert-or-update by natural key, duplicate removal, `ingest_runs` bookkeeping |
| `src/uavert/scoring/bands.py` | New | Bands and score-to-band function, the one place band names are defined |
| `src/uavert/scoring/crime.py` | New | CSI weighting, percentile rank, recency, nearby-cell smoothing, leaning toward the neighbourhood |
| `src/uavert/scoring/environment.py`, `alerts.py`, `news.py` | New | Category scores |
| `src/uavert/scoring/combine.py` | New | Highest-score combination and reason ranking |
| `src/uavert/scoring/route.py` | New | Points along the route → cells → riskiest stretches |
| `src/uavert/scoring/build.py` | New | Runs the scoring over the database and writes the stored score tables |
| `src/uavert/api/app.py` | New | FastAPI app, error handlers, static web files, `/api/v1` router |
| `src/uavert/api/routes/*.py` | New | Endpoints (see Contracts) |
| `src/uavert/api/schemas.py` | New | Pydantic response models |
| `src/uavert/web/index.html`, `app.js`, `style.css`, `rules.html` | New | Leaflet map (from cdnjs), OSM tiles, panels, route planner, news list, the "How scores work" page |
| `tests/unit/*`, `tests/api/*` | New | See Test strategy |

## Contracts

All endpoints:
- live under `/api/v1`
- are read-only, so all are `GET`
- are public for now (no accounts yet), marked as such in the API docs page

The API docs page is at `/api/docs`.

Every successful response looks like this:

```json
{ "data": { ... }, "meta": { "generated_at": "2026-10-06T14:00:00Z",
  "sources": { "tps_mci":   { "as_of": "2026-06-30", "collected_at": "2026-10-05T21:10:00Z" },
               "eccc_aqhi": { "as_of": "2026-10-06T13:00:00Z", "collected_at": "2026-10-06T13:20:00Z" } } } }
```

Every error looks like this:

```json
{ "error": { "code": "address_not_found", "message": "We couldn't find that address in Toronto.", "details": [] } }
```

### Shared score object

```json
{
  "score": 68, "band": "elevated",
  "categories": { "crime": 68, "environment": 12, "alert": 0, "news": 0 },
  "reasons": [
    { "category": "crime", "text": "4 street robberies within about 250 m in the last 12 months",
      "value": 4, "source_key": "tps_mci", "as_of": "2026-06-30", "collected_at": "2026-10-05T21:10:00Z" }
  ]
}
```

### Endpoints

| Endpoint | Purpose | Response `data` | Errors |
|---|---|---|---|
| `GET /api/v1/health` | Database reachable | `{status, database}` | 503 if the database is down |
| `GET /api/v1/neighbourhoods` | All 158 for the map | GeoJSON FeatureCollection; each feature's properties are `{id, name, ...score object without reasons}` | — |
| `GET /api/v1/neighbourhoods/{id}` | Details | `{id, name, population, crime_rates_2025, ...score object}` | 404 `not_found` |
| `GET /api/v1/cells?bbox=minLon,minLat,maxLon,maxLat` | Street layer for the map view | GeoJSON of the cells in view, properties `{h3, score, band, incident_count, top_reason}` | 422 `bbox_too_large` (more than about 25 km², roughly 2,500 cells), 422 `invalid_bbox` |
| `GET /api/v1/risk-scores?address=...` or `?lat=&lon=` | Destination ("where I'm going"); replaces `/v1/score` from the definition | `{location:{query, display_name, lat, lon}, street:{h3, ...score object}, neighbourhood:{id, name, ...score object}}` | 404 `address_not_found`, 422 `outside_coverage`, 502 `upstream_unavailable` |
| `GET /api/v1/route-risks?from=...&to=...` (an address or `lat,lon` each) | Route ("where I'm walking") | `{from, to, distance_m, duration_s, geometry: GeoJSON LineString, score, band, reasons, riskiest_segments:[{geometry, score, band, reasons}]}` | 404 `address_not_found`, 422 `outside_coverage`, 422 `route_too_long`, 422 `no_route`, 502 `upstream_unavailable` |
| `GET /api/v1/news-events?since_hours=24&limit=50` | Recent news | `[{id, headline, url, source, published_at, category, location_text, lat, lon, citywide}]`, newest first | 422 for out-of-range values |
| `GET /api/v1/sources` | How fresh each source is | `[{key, name, licence, attribution, url, last_refreshed_at, last_status, last_error}]` | — |
| `GET /api/v1/scoring-rules` | Feeds the "How scores work" page | `{bands, csi_edition, csi_weights:[...], offence_map:[...], parameters:{half_life_days, min_incidents, ...}}` | — |

**Paging and limits:**
- Lists are short (158 neighbourhoods; at most about 2,500 cells per view; up to 50 news items), so only `news-events` takes `limit`. Full paging comes when there are users and history.
- The risk-scores and route-risks endpoints allow 30 requests per minute per IP, using a simple in-memory counter.
- Geocoding results are cached in memory for 24 hours, to stay within Nominatim's usage policy.

### Command line

```
uavert migrate                   # apply db/migrations in order
uavert ingest reference          # CSI weights, offence map, neighbourhood boundaries and 2025 rates, cells
uavert ingest crime              # Major Crime Indicators + shootings + homicides (2025-01-01 → latest), removing duplicates
uavert ingest live               # AQHI + weather alerts + news (run just before the demo)
uavert ingest all                # all of the above
uavert build-scores              # neighbourhood_scores and cell_scores
uavert serve                     # uvicorn on http://localhost:8000
```

## Review checklist

| Area | Finding |
|---|---|
| Edge cases and errors | **Bad input:** an empty or overly long address gives 422; an address outside Toronto gives 422 `outside_coverage`; the same start and end gives a zero-length route, scored as a destination. **Incidents:** an incident with no location is skipped for cells but kept for neighbourhood totals; an incident whose neighbourhood is "NSA" (not specified) is left out of the neighbourhood totals and counted in the ingest summary. **Live data:** no current alerts or AQHI means category score 0 and the reason "no current reading", never an error. **Quiet cells:** a cell with no incidents takes its neighbourhood's average and the reason says so. |
| Security | Every input is validated by Pydantic (length, number ranges, bbox order). SQL is always parameterised. Errors show a code and message, never stack traces or SQL. The database password lives only in `.env`. CORS is limited to the app's own origin. The request limit protects our use of Nominatim and OSRM. |
| Performance | **Precomputed:** crime scores are stored, so a destination lookup is 1 geocode call (cached) plus 2 indexed lookups, under 2 seconds. **Route:** 1 OSRM call plus about 100–400 cell lookups in a single query, under 3 seconds for a walk of a few km. **Cells layer:** limited by bbox, about 2,500 cells at most, with a simplified hexagon outline. **Ingestion:** about 60,000 incidents for 18 months of data, loaded in pages of 2,000 and written in bulk with COPY (about 1 minute). Neon's free tier (0.5 GB) is plenty. |
| Compatibility | New project, so there are no existing users of the API. The existing browser-only demo stays as it is. The API is `/api/v1` so it can change later without breaking a mobile app. Scores will **differ from the demo**: CSI weights, plus homicides and shootings counted per incident. That difference is expected; see Risks. |
| Testability | Scoring is pure functions, so unit tests use hand-worked numbers. Network clients are passed in and faked with `respx`, so tests never touch live services. API tests run against a **Neon branch** (`test`), a disposable copy of the database, loaded with a small fixture of 3 neighbourhoods, about 30 incidents, 1 alert and 2 news stories. |

## Alternatives considered

1. **GDELT as the main news source (as the plan suggests).** Not chosen as the main source. A live test returned off-topic and foreign-language stories with headlines only, and it allows one request every 5 seconds. CBC Toronto's RSS feed is local, English, includes summaries, and is easier to locate. GDELT stays as a filtered extra.
2. **A language model reading the news** to classify stories and pull out locations. Much more accurate than keywords, but the definition puts it out of scope for this task. It adds an API key and cost, and its output needs evaluating before it can move a public score. It is the natural next step after Tuesday, and the classifier is a single function so it can be swapped in.
3. **Street segments from the City of Toronto road network instead of H3 cells.** More exact for "this stretch of street", but it means loading and matching a road network. H3 is the plan's shared grid for every source and city, and it makes route lookup a simple point-to-cell conversion. Street segments can be added on top later.
4. **Alembic (a migration tool) instead of plain SQL files.** Alembic suits teams using an ORM. Most of our schema is PostGIS/H3 SQL, so plain numbered `.sql` files are clearer and have no extra dependency.

## Risks

| Risk | How it's reduced |
|---|---|
| **Old CSI weights.** The only openly published table is the 2009 edition, and newer weights are not openly listed. | Weights are stored with their edition and shown on the rules page as "Statistics Canada CSI weights (2009 published table)". Action for you: ask StatCan (Canadian Centre for Justice and Community Safety Statistics) for the current weight table. Changing tables is a data change, not code. |
| **Homicides and shootings dominate.** Under CSI, a single homicide (7,042) outweighs about 300 level-1 assaults, so one homicide marks a cell for months. | This is the honest result of official weights. Recency weighting halves it every 6 months. Reasons say plainly "1 homicide, March 2026". During the build I will produce a before-and-after table of neighbourhood rankings (demo weights vs CSI) for you to review before Tuesday. |
| **Wrong offence mapping** for some codes. | Every offence marked `closest` is listed on the rules page. In Major Crime Indicators these are about 1,600 of about 41,000 incidents in the last 12 months (about 4%), mostly "Assault Peace Officer" mapped to assault level 1. |
| **Noisy news.** Keyword matching will misclassify some stories and fail to locate many. | The rules are cautious: news can reach "elevated" at most, it expires after 24 hours, unlocated stories don't change scores, and everything is labelled "unverified" with a link. Before the demo, check the news list by hand. |
| **CBC RSS terms of use.** RSS feeds are generally offered for personal, non-commercial use. | We store only the headline and link, with attribution. This is fine for an internal demo. A licensed news source (or permission) is needed before public launch; recorded in `sources.licence`. |
| **Python 3.14 is new.** Some packages (psycopg-binary, h3, shapely) may not have ready-made installers for 3.14 yet. | The first step of phase 3 is a 10-minute install check. Fallback: install Python 3.12 with `uv` for this project only. |
| **Outside services.** Nominatim, OSRM and CBC are free community or public services with no uptime promise and may be slow or down during the demo. | Caching, timeouts, clear 502 messages. Before the demo, warm the cache by running the demo addresses and routes once. Mapbox can replace them later with a config change. |
| **Neon free tier pauses when idle.** The database sleeps after about 5 minutes of inactivity, and the first request takes 1–2 seconds longer. | Call `/api/v1/health` just before presenting. |
| **Tuesday timeline.** | Build order: data + CSI → street cells → destination/route → news → map polish. Each step is demo-able on its own; phase 3 breaks it into steps that each keep the build working. |

## Test strategy

| Acceptance criterion | How it will be tested |
|---|---|
| 1. 158 neighbourhoods + 12 months of incidents, no duplicates on re-run | Run `ingest reference` + `ingest crime` on a fresh Neon branch. SQL checks: `count(*) = 158`; incident counts match the ArcGIS totals for the date range, minus removed duplicates. Run again: counts unchanged. |
| 2. CSI weights stored; every offence mapped; stops on an unknown offence | Unit test: the mapping covers every UCR code+extension in a recorded sample. Unit test: an unknown code raises a clear error. SQL check that the edition is stored. |
| 3. AQHI + alerts stored | Run `ingest live` against live ECCC; check rows. Unit tests with recorded ECCC responses, including an empty alerts response. |
| 4. Sources and freshness | API test of `/api/v1/sources` after loading the fixture. Collection dates: an SQL check that every row in every data table has `collected_at` set; an API test that every reason and `meta.sources` entry has both `as_of` and `collected_at`; a second ingestion run adds a new `ingest_runs` row and doesn't overwrite the first. |
| 5. Neighbourhood percentile rank with CSI weights | Unit test: 4 made-up neighbourhoods with hand-worked weighted rates and percentiles. |
| 6. Street-cell rules (premises, recency, leaning toward neighbourhood) | Three unit tests, one per rule, with hand-worked numbers. |
| 7. Combined score is the highest, not an average | Unit test: crime 10, AQHI 8 (score 61) → combined 61, band elevated. |
| 8. A warning puts areas in "high" | Unit test plus an API test with a fixture warning polygon. |
| 9. "safe" never used as a label | Unit test of the bands; an API test searches every endpoint's response for `\bsafe\b` in labels and band names. |
| 10. Neighbourhood endpoints | API tests: list (158 in a live check, 3 in the fixture), details with 2–3 reasons, each with source and `as_of`. |
| 11. Cells endpoint | API tests: a valid bbox, too large a bbox (422), a reversed bbox (422). |
| 12. Destination under 2 s | API test with a faked geocoder. Live timing check of `100 Queen St W, Toronto` (reported in phase 5). |
| 13. Route under 3 s with riskiest stretches | Unit test of the route-to-stretches step on a made-up line. API test with faked OSRM. Live timing check of Union Station → Kensington Market. |
| 14. Clear 4xx errors | API tests: unknown address (404), Mississauga address (422), route too long (422), no route (422). |
| 15. News stored and listed | Unit tests of the classifier and place extraction on about 20 real CBC headlines collected today, including today's "Torontonians don't feel safe…" election story, which must **not** be flagged. API test of `/api/v1/news-events`. |
| 16. News raises nearby cells, labelled, gone after 24 h, never above elevated | Unit tests: a story at 0 h scores 74 at its cell, about 37 at 12 h, 0 at 24 h; combined with crime 20 gives 74 (elevated); a story alone never reaches 75. |
| 17. A source being down doesn't break anything | Unit tests with faked timeouts: ingestion records `failed` and keeps old rows; the API returns stored scores with `as_of`; a routing failure gives 502 `upstream_unavailable`. |
| 18. No secrets | Check that `.env` is git-ignored; scan the committed files for `postgres://` or `npg_` patterns. |
| 19. Web map | Run by hand in phase 5 (screenshots), and your own check in phase 6. |
| 20. One-command tests + README | `pytest` passes; the README steps are followed on a clean folder in phase 5. |

## What happens next
Once this design is approved, phase 3 (start the work):
- creates the Git repository and the Neon project, plus a `test` branch of the database
- checks that the Python packages install on 3.14 (falling back to 3.12 if they don't)
- confirms the extensions install on Neon
- writes a step-by-step implementation plan in build order, for your approval before coding starts

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01
- **User's response:** "yes approve just keep track of the dates ofwhen the information is being collected"
- **Revisions before approval:** 2026-10-01: The user approved on the condition that collection dates are tracked. Added the "Collection dates" section, `collected_at`/`as_of` in the API contracts, and a test for this under criterion 4.
