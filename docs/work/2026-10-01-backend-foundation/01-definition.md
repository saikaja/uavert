# 1. Define the work: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved

## What this step is
This step agrees on what is being built and how we will know it is done, before choosing how to build it. Nothing is designed or coded yet.

## What was done
- Read the build plan, `uavert-build-plan.md` (as of October 1, 2026). The relevant sections were Architecture and tech stack, Risk scoring model, Proof of concept, Proof-of-concept demo, Getting to street level, and Risks.
- There is no existing code. The only earlier build is the browser-only demo (the "Uavert Toronto Risk Map" artifact, September 29, 2026). It has no backend: the crime data is built into the page, air quality and alerts are set by hand, and search works only by neighbourhood name.
- Checked this PC: Python 3.14, Node 24 and Git are installed. Docker and Postgres are not. A Neon (hosted Postgres) account is connected.
- Confirmed that Statistics Canada publishes Crime Severity Index (CSI) weights for each offence:
  - each weight comes from court sentencing data (how often an offence leads to prison, and how long the sentence is)
  - the weights are updated every five years
  - published examples: murder 7,042, robbery 583, break and enter 187
- Asked five questions that change what gets built (see Questions answered).

## Goal
Build the first real backend for Uavert, plus a web map that runs on it, for the boss demo on Tuesday, October 6, 2026. It follows the plan's architecture: the data pipeline, risk database, scoring engine and API.

The demo should show, on real Toronto data:
- **Official crime weights:** scores use Statistics Canada's Crime Severity Index weights, not weights we made up.
- **Street-level scores:** a score for every small area of the city (about one city block), not just each neighbourhood.
- **Where I'm going:** a 0 to 100 risk score for a destination address.
- **Where I'm walking:** a 0 to 100 risk score for a walking route, showing its riskiest stretches.
- **Live conditions:** live air quality and official weather alerts.
- **News and protests:** recent news about protests and violent incidents, which can raise nearby scores.

The foundation should support more cities, more data sources and, later, a mobile app without a rewrite.

## In scope

### Repository and database
- A new code repository at `C:\Users\saika\uavert`.
- **Database:** Neon Postgres with the PostGIS and H3 extensions. The schema covers:
  - neighbourhoods and crime incidents
  - street cells (H3 hexagons) and their scores
  - air quality readings, official alerts and news events
  - data sources: the licence, attribution and last refresh time for each

### Data loading
Repeatable Python scripts that load:
- **Toronto Police:**
  - Neighbourhood Crime Rates (2025) and the 158 neighbourhood boundaries
  - Major Crime Indicators incidents for the last 12 months (assault, break and enter, robbery, auto theft, theft over $5,000)
  - Shootings and Homicides incidents for the last 12 months
- **Statistics Canada:** the current CSI offence weights, plus a stored mapping from each Toronto Police offence type to a CSI offence.
- **ECCC:** current Toronto AQHI readings and current weather alerts covering Toronto.
- **News:** recent Toronto news from a free source (GDELT).

### Crime scoring with CSI weights
- Every crime is weighted by its CSI weight, at both neighbourhood and street level. This replaces the demo's hand-picked weights.
- Toronto Police categories don't all match a CSI offence one-for-one. For example:
  - shootings have no CSI offence of their own
  - "assault" covers several CSI levels

  Each mapping is written down in the database, shown on the rules page and covered by a test.

### Street-level scoring
This follows the plan's "Getting to street level" section:
- Incidents go onto H3 cells at resolution 9, about 0.1 km² each, roughly a city block or two.
- **What counts:** only incidents that happened outside, on transit or in commercial places. Incidents inside homes are left out of the street score.
- **Recency:** recent months count more than older ones.
- **Sparse cells:** a cell needs a minimum number of incidents before it is scored on its own. Below that, its score leans toward its neighbourhood's score.
- **Ranking:** each cell is ranked within Toronto to give 0 to 100.

### Destination score ("where I'm going")
Enter an address and get:
- the score of its street cell and of its neighbourhood
- each score's band
- the top reasons and their sources

### Route score ("where I'm walking")
Enter a start and an end, as addresses or points clicked on the map. The backend:
1. gets a walking route from a free OpenStreetMap-based routing service
2. finds every street cell the route passes through
3. returns the route line and an overall risk score from 0 to 100, which is the highest score along the route (one risky stretch is never averaged away)
4. returns the 3 riskiest stretches, each with its reasons

### News and protest signals
A basic first version:
- **Collect and label:** pull recent Toronto news from GDELT and flag reports of protests or demonstrations and of violent incidents (shooting, stabbing, assault, police operation) by matching keywords.
- **Locate:** place each report at a street or neighbourhood when the article names one that can be geocoded. Reports with no usable location are listed citywide for information only and don't change any score.
- **Effect on scores:** a located report raises the scores of nearby cells:
  - reports are labelled "unverified news report", with a link to the article
  - the effect expires after 24 hours
  - news on its own can lift a score to the "elevated" band at most; only an official alert can put an area in "high"

### Rest of the scoring engine
- AQHI is mapped to Health Canada's bands.
- An active official alert moves the area to the top band.
- **Combined score:** the highest of the category scores (crime, environment, alerts, news), never an average.
- **Bands:** four bands (lower, moderate, elevated, high). No band is ever called "safe".
- **Reasons:** the top 2 or 3 reasons behind each score, each with its source and date.

### API
Python + FastAPI, versioned under `/v1`. Endpoints:
- neighbourhood scores for the map, and one neighbourhood's detail
- street-cell scores for the area of the map in view
- score for a destination address
- score for a walking route
- recent news events
- data sources and how fresh each one is
- a health check
- an auto-generated API docs page

### Web map
A page served with the API. It shows:
- neighbourhoods coloured by score, with a street-level layer when zoomed in
- a details panel
- a search box for a destination
- a start-and-end route planner that draws the route and colours its risky stretches
- a list of recent news
- a data-freshness note
- a "How scores work" page that includes the CSI weights and the offence mapping

### Groundwork for scale
- Configuration through environment variables only; no secrets in code.
- A city and region field on every place-based record.
- One shared H3 grid for every data source, so a new city is new data, not a new schema.
- Automated tests for the scoring rules, the CSI mapping and the API.
- A README with setup and run steps.

## Out of scope
These are later tasks:
- User accounts, sign-in, saved places, trusted contacts, health flags and any other personal data. Holding only public data is why a non-Canadian database region is acceptable for now.
- Push notifications and the alert engine (change detection, daily cap).
- Separate day and night scores. The incident data has the time of each incident, so this is a natural next step.
- Adjusting for foot traffic in busy areas. The demo will show incident counts next to scores, so busy downtown streets can be read in context.
- Better news reading: language-model or analyst checks, ACLED (it needs a paid commercial licence), and paid feeds.
- Cities other than Toronto. Travel advisories, wildfire, Alert Ready and water advisories.
- Scheduled background refresh. For the demo, ingestion is run by command and refresh times are shown.
- Production deployment to a public URL, CI/CD, monitoring and the mobile app. The design will note how each fits on later.

## Acceptance criteria

**Data loading**
1. Running the ingestion command against an empty database loads:
   - all 158 Toronto neighbourhoods, with their boundaries and 2025 crime rates
   - the last 12 months of Major Crime Indicators, Shootings and Homicides incidents

   Running it again creates no duplicates.
2. The CSI weights are stored with their source and edition (year of the weight update). Every Toronto Police offence type in the loaded data maps to a CSI weight. Ingestion fails with a clear message if it finds an offence type with no mapping.
3. The ingestion command stores at least one current AQHI reading for Toronto and the current set of ECCC weather alerts for Toronto. The alert set may be empty when there are none.
4. Each source records its name, licence, attribution and last refresh time, and `GET /v1/sources` returns them.

**Scoring**
5. The crime score of each neighbourhood is its percentile rank, within Toronto, of its CSI-weighted crime rate. A unit test checks this against hand-worked examples.
6. Each street cell's crime score:
   - counts only incidents whose premises are outside, transit or commercial
   - gives recent incidents more weight
   - leans toward its neighbourhood's score when the cell has fewer incidents than the set minimum

   A unit test checks each of these three rules.
7. The combined score is the highest of the category scores, never an average. A unit test checks a case with a low crime score and a high AQHI.
8. When an active official alert covers Toronto, every affected area is in the top band ("high"), and its reasons name the alert. A test checks this with a sample alert.
9. No API response or page ever uses the word "safe" as a label. The lowest band is "lower".

**API**
10. `GET /v1/neighbourhoods` returns all 158 neighbourhoods, each with:
    - its combined score (0 to 100) and band
    - its category scores
    - its boundary as GeoJSON

    `GET /v1/neighbourhoods/{id}` returns the top 2 or 3 reasons behind the score, each with its number, source and date.
11. The street-cell endpoint returns cell scores for a requested map area, with each cell's score, band, incident count and top reasons.
12. Destination score: `GET /v1/score?address=100 Queen St W, Toronto` returns:
    - the street-cell score and the neighbourhood score
    - the band and reasons for each

    It answers in under 2 seconds.
13. Route score: for a walking route between two Toronto addresses (test route: Union Station to Kensington Market), the route endpoint returns:
    - the route line
    - an overall score equal to the highest cell score along the route
    - up to 3 riskiest stretches, each with its location, score and reasons

    It answers in under 3 seconds.
14. An address outside Toronto, an address that can't be found, or a route that can't be routed returns a clear error message with a 4xx status code, not a server error.

**News**
15. The news ingestion stores recent Toronto news reports labelled as protest or violent incident, each with its headline, link, time and location (or "citywide"). `GET /v1/news` returns them.
16. A located news report changes scores in these ways:
    - it raises nearby street-cell scores
    - it appears in their reasons, labelled "unverified news report"
    - its effect is gone after 24 hours
    - on its own it never lifts a score above the "elevated" band

    Tests check each of these with sample reports.

**Failures and security**
17. If a live source (AQHI, alerts, news or routing) is unreachable:
    - the last stored data is kept
    - the failure is reported instead of crashing
    - the API still serves scores, showing the age of the data each score is based on

    If routing is down, the route endpoint returns a clear message.
18. There are no secrets in the repository. The database connection comes from an environment variable, and `.env` is git-ignored.

**Web map and tests**
19. The web map, opened from the local server:
    - shows all 158 neighbourhoods coloured by band, and the street-level layer when zoomed in
    - opens the score, reasons and sources for a clicked area or a searched destination
    - draws a planned route with its riskiest stretches highlighted
    - lists recent news
20. The automated test suite passes with one command. The README explains how to set up, ingest, run and test.

## Assumptions
- **Project:** it lives in `C:\Users\saika\uavert` as a new Git repository.
- **Geocoding:** OpenStreetMap Nominatim. It is free with no key, and its fair-use limits are fine for a demo.
- **Walking routes:** a free OpenStreetMap-based routing service. Either a public OSRM walking server (no key) or OpenRouteService (free key) will be chosen in the design. Any of these can be swapped for Mapbox or Google later.
- **News source:** GDELT. It is free and needs no key. ACLED is left out because commercial use needs a paid licence.
- **CSI weights:** the design will use the most recent published edition of the weights and record which one.
  - **Toronto Police categories without an exact CSI match:** each gets the closest CSI offence, recorded in the mapping. For example, shootings map to "discharge firearm with intent".
- **Scale of the CSI weights:** the weights span a very wide range (murder 7,042 against break and enter 187), so homicides and shootings will dominate the rankings far more than in the demo. That follows from using the official weights. The design will show how the neighbourhood ranking changes compared with the demo, so you can see the effect before Tuesday.
- **Demo setup:** the demo runs on this laptop (`localhost`). A public hosted URL is a separate step if you want one.
- **Neon project:** free tier, in the nearest available region (US East). This is acceptable only while the database holds no personal data. A Canadian region is a hard requirement before any user data is added.
- **Timeline:** you chose to have everything working by Tuesday. That is ambitious for 3 working days. Build order, with each step demo-able on its own:
  1. backend and CSI scoring
  2. street level
  3. destination and route scores
  4. news

  If time runs short, the first thing to give is web-map polish, then news accuracy. News will be shown as an early version either way.

## Questions answered
- Where should the database live? → **Neon Postgres** (hosted, PostGIS + H3, free tier)
- Which language for the backend? → **Python + FastAPI**
- What should your boss see on Tuesday? → **Backend + a web map**
- What must be working by Tuesday after the scope grew? → **Everything**: CSI weights, street level, destination and route scores, plus a basic first version of news and protest signals
- Which way does the 0 to 100 score run? → **Risk: higher means riskier**, matching the plan and the existing demo, never labelled "safe"
- (User direction, 2026-10-01) Crime weights → **Statistics Canada Crime Severity Index weights**, replacing the demo's hand-picked weights

## What happens next
Once this is approved, phase 2 (review the design) proposes how to build it:
- the database schema
- the folder layout of the code
- the API contracts
- the CSI offence mapping
- how routes and news are scored
- how ingestion handles failures
- how this foundation grows into more cities, the alert engine, user accounts in a Canadian region and the mobile app

That design also gets your approval before any code is written.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 11:59
- **User's response:** "yes sounds good"
- **Revisions before approval:**
  - 2026-10-01: The user asked for:
    - Statistics Canada CSI weights in place of hand-picked weights
    - street-level scoring
    - destination and walking-route risk scores out of 100
    - news and protest signals that can raise scores

    Scope, acceptance criteria and assumptions were updated to match. The user chose to have all of it working by Tuesday, and chose a risk scale where higher means riskier.
