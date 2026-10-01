# 1–3. Define, design and plan: making it solid, and hosting on Vercel

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved
**Adds to:** the approved definition, design revisions and plans in this folder. It covers phases 1–3 in one document, as with [01-03-time-of-day.md](01-03-time-of-day.md).

## What this step is
This document agrees what each of the six additions does, how it is built and in what order, with one approval, before any code.

## What was done
- **The request.** While the phase 6 checklist was open, the user asked "what else can we add to make this more solid". From the list Claude suggested, they chose:
  - **#1:** back up to a private GitHub repository
  - **#2:** remember address and route lookups between restarts
  - **#3:** refresh live data automatically
  - **#5:** the fairness check from the build plan
  - **#7:** smooth out single homicides
  - and hosting on **Vercel** after the push to GitHub
- **Tools.** GitHub CLI 2.101.0 is signed in as `saikaja`, and no `saikaja/uavert` repository exists yet. Vercel CLI 60.0.1 is signed in as `saikaja`.
- **Vercel's rules,** checked 2026-10-01 ([Python runtime](https://vercel.com/docs/functions/runtimes/python), [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [500 MB Python bundles](https://vercel.com/changelog/python-vercel-functions-bundle-size-limit-increased-to-500mb), [cron pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing)):
  - FastAPI is supported and runs as one function
  - Python 3.12–3.14 are supported
  - Python bundles can be up to 500 MB
  - **Hobby-plan scheduled jobs can run at most once a day.** That is too slow for refreshing air quality, alerts and news, so the frequent refresh runs as a GitHub Actions schedule instead.
- **Census data for the fairness check.** City of Toronto Neighbourhood Profiles, 2021 Census, 158-neighbourhood model: `nbhd_2021_census_profile_full_158model.xlsx`, 1.7 MB, last refreshed 2026-05-27.
  - It has "Median total income of household in 2020 ($)" and "Prevalence of low income (LIM-AT) (%)" for every neighbourhood, numbered like the Toronto Police data. All 158 match.
  - **Preview on today's scores:** the Spearman rank correlation between neighbourhood crime score and median household income is **−0.23**, and with the low-income share **+0.18**. Both are weak. The scores do not mostly follow income.
- **One decision asked:** who can open the Vercel site? → **Public link** (the user's choice; risks below).

## Definition

### Goal
Make the demo harder to break, keep the data fresh without anyone running commands, show that the scores aren't just a proxy for income, stop a single homicide from swinging a neighbourhood, and give the app a link that works from any device.

### In scope
1. **GitHub backup:**
   - a private repository `saikaja/uavert`, with both branches pushed
   - `.env` is never pushed
   - a check after pushing that no secret was uploaded
2. **Saved lookups:**
   - address searches are stored in the database for 30 days, and walking routes for 7 days
   - each saved result records when it was collected
   - a restart, or a new Vercel instance, reuses them
3. **Automatic refresh:**
   - **Local:** `uavert serve` refreshes air quality, alerts and news every 30 minutes in the background. This can be changed, or turned off with `UAVERT_REFRESH_MINUTES=0`.
   - **Hosted:** a GitHub Actions schedule refreshes the live data **every hour**. It also reloads crime and traffic data and rebuilds the scores **daily** at 6 am Toronto time.
4. **Fairness check:**
   - the 2021 census income per neighbourhood is loaded as reference data, with its source and date
   - every `build-scores` run computes how strongly neighbourhood crime scores follow income and low-income share
   - the result is stored with when it was computed, shown on the "How scores work" page and in `/scoring-rules`
   - it is flagged **"review the weights"** if the correlation is strong (|ρ| ≥ 0.5), the test in the build plan
5. **Homicide smoothing:**
   - **Neighbourhood scores:** homicides use the **average of 2023–2025** instead of 2025 alone.
   - **Street scores:** each homicide in the last 3 years counts **⅓**, without fading month by month.
   - Reasons say so, for example "1 homicide in 2023–2025 (3-year average)".
6. **Vercel hosting:**
   - the app runs at a public `*.vercel.app` link, against the same Neon database
   - **search engines are told not to index it**
   - the request limits stay on

### Out of scope
- automatic tests on every push (CI)
- a custom domain
- Vercel's paid plan
- user accounts
- moving the database to Canada (not needed while it holds public data only)

### Acceptance criteria (added to criteria 1–28)
**GitHub backup**

29. `saikaja/uavert` exists and is **private**. `main` and `feature/backend-foundation` are pushed. A search of the pushed repository finds no connection string or password, and `.env` is not in it.

**Saved lookups**

30. After a server restart, a previously searched address and route are answered from the database, without calling Nominatim or OSRM. A test proves this with fake services that fail if they are called.
31. Saved lookups expire: addresses after 30 days, routes after 7. Each saved row has `collected_at`.

**Automatic refresh**

32. The local server refreshes the live sources on a timer. A failure is recorded and doesn't stop the server. A test runs one refresh cycle with a failing source.
33. A GitHub Actions workflow runs `ingest live` hourly and the daily crime and traffic reload with `build-scores`. It uses a repository secret for the database. Its first manual run succeeds.

**Fairness check**

34. `build-scores` stores the two correlations, the number of neighbourhoods and `computed_at`. `/scoring-rules` and the rules page show them with the census source and date.
35. The result is labelled "scores don't mostly follow income" when |ρ| < 0.5, and "review the weights" when |ρ| ≥ 0.5. Unit tests cover both.

**Homicide smoothing**

36. A neighbourhood with 1 homicide in 2025 and none in 2023–2024 gets one third of the homicide weight it got before. Unit test, plus a before/after check of the biggest movers, Bayview Woods-Steeles and Mount Dennis.
37. Homicides from 2023-01-01 on are loaded. Street scores weight each one ⅓ for 3 years.

**Vercel hosting**

38. The Vercel production link serves the map, `/api/v1/health` returns 200, and a destination and a walking route work from the link.
39. Responses carry `X-Robots-Tag: noindex`, and `/robots.txt` disallows all. The database URL is set only as a Vercel environment variable.

## Design

### 1. GitHub
`gh repo create saikaja/uavert --private --source . --remote origin`, then push both branches. Before pushing, check that `git ls-files` contains no `.env` and no `npg_` passwords. After pushing, search the remote copy for them too.

### 2. Saved lookups (`db/migrations/005_lookup_cache.sql`)
- **`geocode_cache`:** `query_key` (normalised text, primary key), `found`, `display_name`, `lon`, `lat`, `collected_at`.
- **`route_cache`:** `route_key` (start and end rounded to 5 decimals, about 1 m), `coordinates` (jsonb), `distance_m`, `duration_s`, `collected_at`.
- **Lookup order:** `Geocoder.search` and `Router.walk` first check memory, then the database (within the expiry time), then the outside service. They then write the answer to both.
- **"Not found" answers** are saved too, so repeated typos don't call Nominatim again.
- **No database configured** (unit tests): the services behave as before.

### 3. Automatic refresh
- **Local:** in the app's startup, when `UAVERT_REFRESH_MINUTES > 0` (default 30 for `serve`, 0 in tests), start a background task. Every N minutes it runs the same steps as `ingest live` (AQHI, alerts, CBC, GDELT), each recorded in `ingest_runs` as today. Errors are logged and the loop continues.
- **Vercel:** functions don't run between requests, so the hosted refresh comes from **`.github/workflows/refresh.yml`**:
  - schedule `17 * * * *` (hourly): `python -m uavert ingest live`
  - schedule `0 10 * * *` (06:00 Toronto in summer, 05:00 in winter): `ingest crime`, `ingest traffic`, then `build-scores`
  - it can also be run by hand
  - it uses Python 3.12 on Ubuntu, `uv`, and the `DATABASE_URL` repository secret
- **Budget:** about 24 short runs a day uses roughly 30–40 of GitHub's 2,000 free private-repo minutes per day, about 1,000–1,200 a month.

### 4. Fairness check
- **`scripts/build_neighbourhood_income.py`:** reads the census spreadsheet (downloaded, or a local path) and writes `data/neighbourhood_income_2021.csv`, with source URL and retrieval-date header lines. `openpyxl` is needed only by this script, as a dev dependency.
- **`ingest reference`** loads the CSV into a new table, `neighbourhood_census` (external id, median household income, low-income %, census year, `collected_at`), under a new source, `toronto_census_2021`.
- **`scoring/fairness.py`** (pure functions): Spearman ρ with ties averaged, and the label: |ρ| < 0.5 → "scores don't mostly follow income"; otherwise → "review the weights".
- **`build-scores`** stores one row per run in a new table, `fairness_checks`: `computed_at`, `rho_income`, `rho_low_income`, `n`, `label`, `census_year`.
- **`/scoring-rules`** gains a `fairness` section with the latest check. The rules page shows it in plain language, with a scatter of score against income left as a follow-up.

### 5. Homicide smoothing
- **`ingest crime`:** start date per source. Homicides from **2023-01-01**, others from 2025-01-01 as before.
- **Neighbourhood:** homicide counts = count over 2023–2025 ÷ 3; other offences use 2025 as before.
- **Street:** homicides in the last 3 years count at ⅓ of their CSI weight, with no recency decay. Other offences use 12 months with recency, as before.
- **Reasons:** "1 homicide in 2023–2025 (3-year average)".
- **`csi-vs-demo-ranking.md`** is regenerated, so the before and after are visible.

### 6. Vercel
- **Entry point:** a root `index.py` that exposes `app`. Vercel detects FastAPI apps there.
- **`vercel.json`:** routes everything to the function, with region `cle1` (Cleveland) to sit next to the Neon database in Ohio.
- **Database pool:** created on first use rather than only at startup, so it works however Vercel starts the function. Direct Neon host, pool max 2.
- **Settings:** `DATABASE_URL` is set with `vercel env add` (production). Background refresh is off on Vercel (`UAVERT_REFRESH_MINUTES=0`).
- **No indexing:** middleware adds `X-Robots-Tag: noindex, nofollow`, and `/robots.txt` disallows everything.
- **Deploying:** the first production deploy is made with `vercel --prod` from the tested branch. The Vercel project is connected to the GitHub repository, so later pushes create preview deployments and pushes to `main` go to production. Merging the branch into `main` waits for your phase 6 sign-off, as the workflow requires.

### Review checklist

| Area | Finding |
|---|---|
| Security | **Secrets:** the database URL lives in Vercel and GitHub secret stores only; nothing secret is committed. **Public site:** the request limits stay; saved lookups reduce calls to the free services; no new inputs. |
| Edge cases | **Expired lookups** are refreshed. **A failing scheduled refresh** records `failed` and keeps old data, as today. **Census numbers** missing for a neighbourhood leave it out of the correlation, and the count used is shown. |
| Performance | **Vercel cold start:** about 1–3 s on the first request after idle, plus Neon waking. **Lookups:** one indexed read each. **Fairness check:** 158 values, instant. |
| Compatibility | **API:** fields added only (`fairness` on `/scoring-rules`). **Scores:** homicide smoothing changes some neighbourhood and street scores, which is intended. |
| Testability | Fake services that fail if called (criterion 30); a one-cycle refresh test; fairness and homicide unit tests; a live check against the Vercel link. |

### Risks

| Risk | How it's reduced |
|---|---|
| **The public link spreads** and the free services (Nominatim, OSRM) block us, or traffic grows. | Saved lookups, the request limit per instance, and no indexing. Mapbox is the paid fallback, a config change. |
| **CBC's feed** is for personal, non-commercial use, and a public site shows its headlines. | **Accepted by the user** by choosing a public link. Before wider sharing, switch to a licensed news source or hide news on the hosted site. |
| **A public map of named neighbourhood risk** before the resident testing. | Scores are labelled guidance with sources; the fairness check is published on the rules page; nothing is labelled safe. |
| **Vercel's Python runtime** differs from local (Linux, Python 3.12, no Windows quirks). | `tzdata` is already declared. The first deploy is checked against criterion 38 before you share the link. |
| **GitHub Actions minutes** run out on a private repository. | Hourly, not every 30 minutes (about 1,000–1,200 of 2,000 free minutes a month). The frequency can be lowered. |

## Plan
These steps run on `feature/backend-foundation`, each with tests and a commit.

| # | What | Done when |
|---|---|---|
| S1 | Push to a private GitHub repository (criterion 29) | Repository private; both branches on GitHub; secret search of the remote copy is clean |
| S2 | Saved lookups: migration, geocoder and router use the database (criteria 30–31) | Tests pass; a live restart test shows no outside calls for a repeated search |
| S3 | Homicide smoothing (criteria 36–37) | Tests; `ingest crime` and `build-scores`; ranking report regenerated |
| S4 | Fairness check: script, CSV, table, computation, API and rules page (criteria 34–35) | Tests; `build-scores` stores the check; rules page shows it |
| S5 | Local background refresh, and the GitHub Actions workflow with its secret (criteria 32–33) | Tests; workflow run by hand succeeds on GitHub |
| S6 | Vercel: entry point, `vercel.json`, lazy pool, no indexing, environment variable, production deploy, Git connection (criteria 38–39) | The live link passes `scripts/acceptance_check.py <link>` and the noindex checks |
| S7 | Tests again (phase 5 addendum) and the phase 6 checklist updated with the hosted link | Full suite and both acceptance-check runs pass; documents updated |

## What happens next
Once this is approved, I build S1–S7 in order.

**Two steps act outside this computer, under your accounts:**
- **S1** creates the private GitHub repository
- **S6** deploys a public Vercel site

Approving this document approves both.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 14:05
- **User's response:** "yes"
- **Revisions before approval:** none
