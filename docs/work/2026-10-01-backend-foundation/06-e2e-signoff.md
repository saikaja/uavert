# 6. End-to-end testing: Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval

## What this step is
You use the app yourself, the way your boss will, and record what happens. This is the final sign-off. Claude prepared the checklist but did not run it; only results you report are recorded here.

## What was done
Prepared the commands to run the app, the checklist and a demo-day routine. The checklist is built from the acceptance criteria in [01-definition.md](01-definition.md), [01-03-time-of-day.md](01-03-time-of-day.md) and [01-03-solidify.md](01-03-solidify.md) (criteria 1–39). The items phase 5 could not verify come first ([05-test-report.md](05-test-report.md) and [05-test-report.solidify.md](05-test-report.solidify.md), "Could not verify").

**Updated 2026-10-01**, after the solidify additions:
- the hosted link
- rows 23–29 (fairness check, homicide smoothing, saved lookups, automatic refresh, GitHub)

## What changed
A working first version of Uavert for Toronto: a backend that collects public data and turns it into risk scores, a versioned API, and a web map on top.
- **Data:**
  - Toronto Police crime incidents, weighted by Statistics Canada's Crime Severity Index
  - City of Toronto pedestrian counts, and Bike Share trips for night-time
  - live Environment Canada air quality and weather alerts
  - CBC and GDELT news about protests and violent incidents

  Every record keeps the date it refers to and when it was collected.
- **Scores (0–100, higher means more reported risk, never "safe"):**
  - per neighbourhood
  - per street block, per person on foot
  - for a destination
  - for a walking route, with the stretches that stand out
  - all-day, or at any hour you choose
- **Where it is:**
  - **hosted:** https://uavert.vercel.app (public, not indexed by search engines)
  - **code:** https://github.com/saikaja/uavert (private), branch `feature/backend-foundation`. `main` has only the first planning documents and the refresh workflow.
  - **local copy:** `C:\Users\saika\uavert`
  - **database:** Neon project `uavert` (branches `main` and `test`), shared by the local app and the hosted site
  - **data refresh:** GitHub Actions, hourly (air quality, alerts, news) and daily (crime, traffic, scores)
  - the full record of decisions is in this task folder

## How to run it
**Easiest:** open **https://uavert.vercel.app**. Nothing to install. The data is refreshed hourly by GitHub Actions.

**Locally,** in **PowerShell** (the local app also refreshes live data every 30 minutes while it runs):

```powershell
cd C:\Users\saika\uavert

# Only if the server from our session is still running in the background: stop it so port 8000 is free.
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# 1. Refresh the live data (air quality, alerts, news). About 10 seconds.
.\.venv\Scripts\python.exe -m uavert ingest live

# 2. Start the app. Leave this window open.
.\.venv\Scripts\python.exe -m uavert serve
```

Then open **http://localhost:8000** in your browser.

Optional, in a **second** PowerShell window, to wake the database and cache the demo searches:

```powershell
cd C:\Users\saika\uavert
.\.venv\Scripts\python.exe scripts\warm_demo.py
```

It should end with `Ready.`

**Notes:**
- "GDELT … FAILED … 429" during `ingest live` is expected sometimes (GDELT limits requests). It is shown in the app and doesn't affect anything else.
- If you ever set this up on another computer, follow the README's "Set up" section first.

## E2E checklist
Fill in **Result** with Passed, Failed or Not tested, and add notes for anything odd. Rows 1–14 are the ones phase 5 couldn't check in a real browser.

| # | Steps | Expected result | Result | Notes |
|---|---|---|---|---|
| 1 | Open http://localhost:8000 | A map of Toronto with 158 neighbourhoods coloured in 4 shades, a legend ("Lower reported risk" … "High risk"), and a panel on the left: When, Where I'm going, Where I'm walking, Recent news, Data collected | Not tested | |
| 2 | Click any neighbourhood | The panel shows its name, a score badge (0–100) with its band, bars for Crime / Air quality / Official alerts / News, and 2–3 reasons, each with a source, a data date and a collected date | Not tested | |
| 3 | Zoom in to downtown (about 5 clicks on +) | Neighbourhood colours fade and small hexagons (street blocks) appear. Hovering one shows "Street score …, … its surroundings, about … people an hour on foot". The "Zoom in" hint disappears | Not tested | |
| 4 | Click a street hexagon | The panel shows the street score with reasons, "Showing: All day", the incident count, foot traffic and "× the reported street crime of the surrounding 1 km"; the neighbourhood score is below it | Not tested | |
| 5 | **Where I'm going:** type `100 Queen St W` and press Check | Within about 2 seconds a marker appears at City Hall, the map zooms there, and the panel shows the street score (about 84, high) with reasons, including "Busy area: about 1,378 people an hour on foot nearby…" | Not tested | |
| 6 | **Where I'm walking:** From `Union Station`, To `Kensington Market`, press Check walk | Within about 3 seconds a blue route line appears, about 2.8 km / 37 min. One thicker coloured stretch near Kensington stands out. The panel lists "Stretches that stand out" with "2.7× the reported street crime of its surroundings, per person" | Not tested | |
| 7 | With the walk from row 6 still shown, set **When** to `2 am` | The walk re-runs on its own. The panel says "Showing: 2 am"; the score rises (about 100); the first reason starts "At 2 am: … estimated from Bike Share trips" | Not tested | |
| 8 | Set **When** to `2 pm`, then search `100 Queen St W` again | "Showing: 2 pm"; the street score is lower than at 2 am (about 87 against 99); the first reason starts "At 2 pm: … (City pedestrian counts)" | Not tested | |
| 9 | Zoomed in on downtown, switch **When** quickly between a few hours, ending on `11 pm` | The hexagon colours settle on the last choice (11 pm); no flicker back to an earlier hour | Not tested | |
| 10 | Set **When** to `All day` and click a neighbourhood | The neighbourhood score is unchanged by the time setting (neighbourhood colours are all-day) | Not tested | |
| 11 | Look at **Recent news** | Either "No protest or violent-incident reports in Toronto news in the last 24 hours", or headlines marked unverified with a type, location (or "location unknown (not scored)"), publisher and time. Clicking a headline opens the article in a new tab | Not tested | |
| 12 | Look at **Data collected** | Every source listed with "data up to …" and "collected …" dates. Weather alerts says "nothing current" when none are active. GDELT may say "latest attempt failed, showing earlier data" | Not tested | |
| 13 | Open the page on your **phone** or with a narrow browser window (under about 760 px) | The map sits on top and the panel below; no sideways scrolling; buttons and fields are usable | Not tested | (needs the phone on the same network, or test with a narrow desktop window) |
| 14 | Click **How scores work** | A page explaining the four parts and the highest-score rule, bands, street level, "Allowing for crowds", "Time of day" with a 24-hour table (measured and estimated hours), CSI weights, the offence mapping, limitations, and sources with collection dates | Not tested | |
| 15 | **Error:** Where I'm going → `100 City Centre Dr, Mississauga` | A red message: "… is outside the area we cover. Uavert currently covers the City of Toronto." No crash | Not tested | |
| 16 | **Error:** Where I'm going → `zzqqxx nowhere 12345` | "We couldn't find … Try adding a street number or 'Toronto'." | Not tested | |
| 17 | **Error:** walk from `Union Station` to `Scarborough Town Centre` | "Those places are 17.6 km apart; walking routes are limited to 10 km." | Not tested | |
| 18 | **Error (service offline):** stop the server (Ctrl+C in its window), click Check in the browser, then restart it with `.\.venv\Scripts\python.exe -m uavert serve` | While stopped: an error message in the panel, not a broken page. After restarting and reloading, everything works again | Not tested | |
| 19 | Look at every score and label on the map, panels and rules page | The word "safe" never appears as a rating or band; the lowest band reads "Lower reported risk" | Not tested | |
| 20 | Open http://localhost:8000/api/docs | The interactive API page lists the `/api/v1` endpoints: health, neighbourhoods, cells, risk-scores, route-risks, news-events, sources, scoring-rules | Not tested | |
| 21 | In the second PowerShell window: `.\.venv\Scripts\python.exe scripts\acceptance_check.py` | Ends with "22 of 22 checks passed" | Not tested | |
| 22 | Check the comparison report: open `docs\work\2026-10-01-backend-foundation\csi-vs-demo-ranking.md` (regenerated with the 3-year homicide average; see its last section) | It reads sensibly to you. Is the ranking with StatCan weights acceptable to show? | Not tested | (your judgement) |
| 23 | **Hosted site:** open https://uavert.vercel.app on your laptop **and on your phone** (mobile data is fine), and repeat rows 2, 5, 6 and 7 there | The same map and results as locally; searches answer within a couple of seconds. On the phone, the map sits above the panel | Not tested | |
| 24 | On the hosted site, click **How scores work** and find **Fairness check** | It says "Scores don't mostly follow income. Across 158 neighbourhoods, scores vs median household income: -0.28; vs share of low-income households: 0.24. Checked … against the 2021 Census." | Not tested | |
| 25 | Click **Bayview Woods-Steeles** on the map, then **Mount Dennis** | A homicide reason, if shown, reads "1 homicide in 2023-2025 (3-year average; …)". Neither is near the top of the city any more | Not tested | |
| 26 | **Saved lookups:** stop and restart the local server, then search `100 Queen St W` | It answers about as fast as before the restart (the answer is saved in the database) | Not tested | |
| 27 | **Automatic refresh:** after a few hours, open https://github.com/saikaja/uavert/actions | "Refresh data" has run on schedule about every hour, with green ticks. A yellow warning about GDELT is normal | Not tested | |
| 28 | On the hosted site, look at **Data collected** later in the day | Air quality and news show a "collected" time within roughly the last hour | Not tested | |
| 29 | Open https://github.com/saikaja/uavert in a private or incognito window (signed out) | GitHub shows "404 – not found", which confirms the repository is private | Not tested | |

**Not possible to test on demand** (recorded so they aren't forgotten):
- **A real Environment Canada warning:** if one is active for Toronto on demo day, covered areas should show "High risk" with "Environment Canada … warning in effect".
- **A real news report** of a Toronto shooting or protest: it should appear in Recent news as unverified and raise nearby blocks for 24 hours, at most to "elevated".

## Demo-day routine (Tuesday)
1. 15–30 minutes before, **either:**
   - **present from https://uavert.vercel.app** (recommended; it works from any device). Open it and click one neighbourhood to wake the database. Or run `.\.venv\Scripts\python.exe scripts\warm_demo.py https://uavert.vercel.app` and wait for `Ready.`
   - **or** run locally: the two commands in "How to run it" (`ingest live`, then `serve`), then `scripts\warm_demo.py`, and wait for `Ready.`
2. Open http://localhost:8000 and click one neighbourhood, so the database is awake.
3. **A suggested story for your boss:**
   1. the city map (neighbourhoods, with StatCan weights)
   2. zoom into downtown (street level, allowing for crowds)
   3. `100 Queen St W` (destination, with reasons and data dates)
   4. Union Station → Kensington Market (the stretch that stands out)
   5. switch **When** to 2 am (later at night, emptier streets, higher score)
   6. "How scores work" and "Data collected" (where every number comes from)
4. **If a search is slow or fails,** it's the free address or route service (Nominatim or OSRM). Try again, or use a search you warmed up in step 1.

## Known limitations
- **Toronto only;** neighbourhood scores are all-day; no accounts, alerts to phones, or day-of-week patterns yet.
- **Weights:** StatCan's 2009 published weights; one homicide moves a small neighbourhood a lot ([csi-vs-demo-ranking.md](csi-vs-demo-ranking.md)).
- **Night-time foot traffic** is estimated from Bike Share trips; daytime counts are snapshots from 2015–2026.
- **News** is keyword-matched and unverified. CBC's feed is for personal, non-commercial use (fine for an internal demo, not a public launch). GDELT often refuses requests.
- **Free services:** address search and walking routes use free OpenStreetMap services with no uptime guarantee. The database is in Neon's US East (Ohio) region; it holds public data only, and a Canadian region is required before any user data is added.
- **Public hosted link:** https://uavert.vercel.app is open to anyone with the link (your choice). It shows CBC headlines, whose feed is for personal, non-commercial use. Switch to a licensed news source, or hide news on the hosted site, before sharing widely.
- **Don't push to `main` before merging:** Vercel deploys `main` to production. Until the app is merged there after your sign-off, a push to `main` would replace the working site with `main`'s current content.
- **Local installs:** must use the README's editable install (`-e`).
- **Licences:** the City of Toronto traffic dataset's licence says "not specified" on its page; confirm before a public launch.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
