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

**Changed 2026-10-15 ([01-03-time-map.md](01-03-time-map.md)):** "Where I'm going" was removed. Wherever a row says to search an address, zoom in and click that spot on the map instead (or use it as the "To" of a walk). Rows 1, 5, 10, 15 and 16 were reworded; the band colours are now green, yellow, orange and red; rows 44–47 are new.

| # | Steps | Expected result | Result | Notes |
|---|---|---|---|---|
| 1 | Open http://localhost:8000 | A map of Toronto with 158 neighbourhoods coloured in 4 shades, a legend ("Lower reported risk" green, "Moderate risk" yellow, "Elevated risk" orange, "High risk" red), and a panel on the left: When, Where I'm walking, Recent news, Data collected | Not tested | |
| 2 | Click any neighbourhood | The panel shows its name, a score badge (0–100) with its band, bars for Crime / Air quality / Official alerts / News, and 2–3 reasons, each with a source, a data date and a collected date | Not tested | |
| 3 | Zoom in to downtown (about 5 clicks on +) | Neighbourhood colours fade and small hexagons (street blocks) appear. Hovering one shows "Street score …, … its surroundings, about … people an hour on foot". The "Zoom in" hint disappears | Not tested | |
| 4 | Click a street hexagon | The panel shows the street score with reasons, "Showing: All day", the incident count, foot traffic and "× the reported street crime of the surrounding 1 km"; the neighbourhood score is below it | Not tested | |
| 5 | Zoom in to City Hall (Queen St W at Bay St) and click the street block in front of it | Within about 2 seconds a marker appears there, and the panel shows the street score (about 64, elevated) with reasons: the most common offence nearby first, then "About 3.9× the reported street crime per person of a typical Toronto block; busy area with about 1,378 people an hour on foot…" | Not tested | |
| 6 | **Where I'm walking:** From `Union Station`, To `Kensington Market`, press Check walk | Within about 3 seconds a blue route line appears, about 2.8 km / 37 min. One thicker coloured stretch near Kensington stands out. The panel says "mostly … ; worst block shown" and lists "Stretches that stand out" with "… × the reported street crime of its surroundings, per person" | Not tested | |
| 7 | With the walk from row 6 still shown, set **When** to `2 am` | The walk re-runs on its own. The panel says "Showing: 2 am"; the score rises; the first reason starts "At 2 am: … estimated from Bike Share trips" | Not tested | |
| 8 | Set **When** to `2 pm`, then search `100 Queen St W` again | "Showing: 2 pm"; the street score is lower than at 2 am (about 69 against 100); the first reason starts "At 2 pm: … (City pedestrian counts)" | Not tested | |
| 9 | Zoomed in on downtown, switch **When** quickly between a few hours, ending on `11 pm` | The hexagon colours settle on the last choice (11 pm); no flicker back to an earlier hour | Not tested | |
| 10 | Zoomed out, set **When** to `2 am`, then to `2 pm` | The neighbourhood colours change: downtown (e.g. Kensington-Chinatown) turns red at 2 am and lighter at 2 pm; quiet areas like Guildwood barely change. Hovering shows "…: 91 at 2 am" | Not tested | |
| 11 | Look at **Recent news** | Either "No protest or violent-incident reports in Toronto news in the last 24 hours", or headlines marked unverified with a type, location (or "location unknown (not scored)"), publisher and time. Clicking a headline opens the article in a new tab | Not tested | |
| 12 | Look at **Data collected** | Every source listed with "data up to …" and "collected …" dates. Weather alerts says "nothing current" when none are active. GDELT may say "latest attempt failed, showing earlier data" | Not tested | |
| 13 | Open the page on your **phone** or with a narrow browser window (under about 760 px) | The map sits on top and the panel below; no sideways scrolling; buttons and fields are usable | Not tested | (needs the phone on the same network, or test with a narrow desktop window) |
| 14 | Click **How scores work** | A page explaining the five parts and the highest-score rule, "What the numbers mean" (typical block = 25, 2× = 45…), bands, street level, "Allowing for crowds", "Time of day" with a 24-hour table (measured and estimated hours), CSI weights, the offence mapping, limitations, and sources with collection dates | Not tested | |
| 15 | **Error:** walk from `Union Station` to `100 City Centre Dr, Mississauga` | A red message: "… is outside the area we cover. Uavert currently covers the City of Toronto." No crash | Not tested | |
| 16 | **Error:** walk from `Union Station` to `zzqqxx nowhere 12345` | "We couldn't find … Try adding a street number or 'Toronto'." | Not tested | |
| 17 | **Error:** walk from `Union Station` to `Scarborough Town Centre` | "Those places are 17.6 km apart; walking routes are limited to 10 km." | Not tested | |
| 18 | **Error (service offline):** stop the server (Ctrl+C in its window), click Check in the browser, then restart it with `.\.venv\Scripts\python.exe -m uavert serve` | While stopped: an error message in the panel, not a broken page. After restarting and reloading, everything works again | Not tested | |
| 19 | Look at every score and label on the map, panels and rules page | The word "safe" never appears as a rating or band; the lowest band reads "Lower reported risk" | Not tested | |
| 20 | Open http://localhost:8000/api/docs | The interactive API page lists the `/api/v1` endpoints: health, neighbourhoods, cells, risk-scores, route-risks, news-events, sources, scoring-rules | Not tested | |
| 21 | In the second PowerShell window: `.\.venv\Scripts\python.exe scripts\acceptance_check.py` | Ends with "26 of 26 checks passed" | Not tested | |
| 22 | Check the comparison report: open `docs\work\2026-10-01-backend-foundation\csi-vs-demo-ranking.md` (regenerated with the 3-year homicide average; see its last section) | It reads sensibly to you. Is the ranking with StatCan weights acceptable to show? | Not tested | (your judgement) |
| 23 | **Hosted site:** open https://uavert.vercel.app on your laptop **and on your phone** (mobile data is fine), and repeat rows 2, 5, 6 and 7 there | The same map and results as locally; searches answer within a couple of seconds. On the phone, the map sits above the panel | Not tested | |
| 24 | On the hosted site, click **How scores work** and find **Fairness check** | It says "Scores don't mostly follow income. Across 158 neighbourhoods, scores vs median household income: -0.28; vs share of low-income households: 0.24. Checked … against the 2021 Census." | Not tested | |
| 25 | Click **Bayview Woods-Steeles** on the map, then **Mount Dennis** | A homicide reason, if shown, reads "1 homicide in 2023-2025 (3-year average; …)". Neither is near the top of the city any more | Not tested | |
| 26 | **Saved lookups:** stop and restart the local server, then search `100 Queen St W` | It answers about as fast as before the restart (the answer is saved in the database) | Not tested | |
| 27 | **Automatic refresh:** after a few hours, open https://github.com/saikaja/uavert/actions | "Refresh data" has run on schedule about every hour, with green ticks. A yellow warning about GDELT is normal | Not tested | |
| 28 | On the hosted site, look at **Data collected** later in the day | Air quality and news show a "collected" time within roughly the last hour | Not tested | |
| 29 | Open https://github.com/saikaja/uavert in a private or incognito window (signed out) | GitHub shows "404 – not found", which confirms the repository is private | Not tested | |
| 30 | **Your example walk:** From `Union Station`, To `125 Blue Jays Way`, **When** `All day` | Score about **53 (elevated)**, not "High"; the panel says "mostly moderate (35)"; first reason is the most common offence (assaults), second "About 2.7× … a typical Toronto block…". Does this feel right to you now? | Not tested | (your judgement) |
| 31 | Click **How scores work** and read **What the numbers mean** and **Official alerts** | A table: half as much = 5, typical = 25, 2× = 45, 4× = 65, 8× = 85; alerts follow Environment Canada's colours (yellow moderate, orange elevated, red high) | Not tested | |
| 32 | Search an address near **Rogers Centre** (for example `125 Blue Jays Way`) | Among the reasons (if room) or on the rules page: "Near Rogers Centre: can draw about 39,150 people on event days"; the Crowds bar stays 0 on non-event days | Not tested | |
| 33 | **On Saturday October 3, evening** (Nuit Blanche): search `100 Queen St W` | The Crowds bar shows 35 and a reason "Nuit Blanche 2026 today, about … m away: large crowds and road closures expected" | Not tested | (only testable on Oct 3–4) |
| 34 | **If a heat warning is ever active** (summer): search any address in the warned area | A reason "Environment Canada heat warning in effect. Nearest cool space: … about … m away, open until …" | Not tested | (only testable during a heat alert) |
| 35 | **Odds (added 2026-10-07):** on https://uavert.vercel.app search `100 Queen St W` | Under the score: "Odds in Yonge-Bay Corridor (2025), per resident", with a table: High 1 in 110 (Toronto 1 in 470), Medium 1 in 47 (220), Low 1 in 47 (140), Any 1 in 19 (73), and the note "One reported incident a year for every N residents. Not a personal prediction…". Is the wording clear to you? | Not tested | (your judgement) |
| 36 | Click any neighbourhood on the map (zoomed out) | The same odds table appears for that neighbourhood, after its reasons | Not tested | |
| 37 | Search `150 Horner Ave` (Mimico-Queensway, near the jail) | Neighbourhood score **24 (lower reported risk)**, not 40; odds Medium about 1 in 310, not 1 in 28 | Not tested | |
| 38 | Click **How this is worked out** under the odds; also check rows 35–37 **on your phone** | The rules page opens at "Odds per resident" with the three severity levels; "Limitations" names the two jails. On the phone, the table fits the screen without sideways scrolling | Not tested | |
| 39 | **Trends (added 2026-10-08, [01-03-trends.md](01-03-trends.md)):** once deployed, search `100 Queen St W` | Under the odds: "Trend in Yonge-Bay Corridor, per 1,000 residents", a chart with a solid line, a dashed trendline and a faint Toronto line, and the summary "Violent crime: falling, −38% over 2016–2025 (Toronto: rising, +10%)" and "Property crime: falling, −35% … (Toronto: roughly flat, +5%)". Is it clear to you? | Not tested | (your judgement) |
| 40 | Click **5 years**, then **Property** | Violent changes to "rising, +31% over 2021–2025 (Toronto: rising, +17%)"; the chart redraws for 2021–2025 and then shows property crime | Not tested | |
| 41 | Open **By offence** and **Yearly figures** | 9 offences with their 2025 counts (small ones say "too few to call a trend"); a year-by-year table for the neighbourhood and Toronto | Not tested | |
| 42 | Click a neighbourhood on the map, e.g. Guildwood; then **How this is worked out**; check rows 39–41 **on your phone** | Guildwood shows its own trend ("roughly flat"), with its line below Toronto's. The rules page opens at "Trends over time". On the phone, the chart and buttons fit without sideways scrolling | Not tested | |
| 43 | **Odds % and score label (added 2026-10-14, [01-03-odds-percent.md](01-03-odds-percent.md)):** once deployed, search `100 Queen St W`, then click Kingsview Village-The Westway; check both **on your phone** | Above the band: "Risk score (0–100, higher = riskier)". Odds cells read e.g. "1 in 110 (0.94%)" and "1 in 470 (0.21%)"; the note says "(P% of the population)". The table fits the phone screen. Are the percentages clear, and does the label answer "is this a safety score"? | Not tested | (your judgement) |
| 44 | **Time on the map (added 2026-10-15, [01-03-time-map.md](01-03-time-map.md)):** set **When** to `2 am`, then click **Kensington-Chinatown** | The panel says "Showing: 2 am · Neighbourhood …", the score is about 91 (High risk, red badge), and a reason reads "At 2 am: street blocks here typically score about 36 points higher than all day, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)". The odds and trend headings end with "(yearly)". Does the change make sense to you? | Not tested | (your judgement) |
| 45 | With Kensington-Chinatown still open, change **When** to `2 pm` | The panel updates by itself to "Showing: 2 pm" with a lower score (about 43) | Not tested | |
| 46 | Look at the panel and the map legend | No "Where I'm going" section. The legend reads green "Lower reported risk", yellow "Moderate risk", orange "Elevated risk", red "High risk", and the map, badge and bars use the same colours. Are yellow and orange easy to tell apart? | Not tested | (your judgement) |
| 47 | Repeat rows 44 and 46 **on your phone** | Same results; the map sits above the panel with no sideways scrolling | Not tested | |

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
- **Toronto only;** no accounts, alerts to phones, or day-of-week patterns yet.
- **Weights:** StatCan's 2009 published weights; one homicide moves a small neighbourhood a lot ([csi-vs-demo-ranking.md](csi-vs-demo-ranking.md)).
- **Night-time foot traffic** is estimated from Bike Share trips; daytime counts are snapshots from 2015–2026.
- **News** is keyword-matched and unverified. CBC's feed is for personal, non-commercial use (fine for an internal demo, not a public launch). GDELT often refuses requests.
- **Free services:** address search and walking routes use free OpenStreetMap services with no uptime guarantee. The database is in Neon's US East (Ohio) region; it holds public data only, and a Canadian region is required before any user data is added.
- **Public hosted link:** https://uavert.vercel.app is open to anyone with the link (your choice). It shows CBC headlines, whose feed is for personal, non-commercial use. Switch to a licensed news source, or hide news on the hosted site, before sharing widely.
- **Don't push to `main` before merging:** Vercel deploys `main` to production. Until the app is merged there after your sign-off, a push to `main` would replace the working site with `main`'s current content.
- **Local installs:** must use the README's editable install (`-e`).
- **Licences:** the City of Toronto traffic dataset's licence says "not specified" on its page; confirm before a public launch.

## Merged before sign-off
On 2026-10-07, Sai asked to merge `feature/backend-foundation` into `main` ("merge") before testing, after being told rows 1–38 were untested. It was merged at `261c0fb`, keeping the branch's `vercel.json`, which turns production deploys from `main` back on. **This is not an end-to-end sign-off:** the checklist above still needs Sai's results, and anything that fails is fixed on `main`.

Also on 2026-10-07, with Sai's approval ("yes"), the GitHub Actions variable `DATA_BRANCH` was deleted, so the data refresh now runs from `main`. The first run afterwards (`37678808823`) checked out `refs/heads/main` and succeeded. The feature branch is kept on GitHub for reference.

**Fix after Sai's first look (2026-10-07):** Sai reported "i cannot see the odds score". The odds were rendering, but at the bottom of the results panel, below every reason, which is out of view on a laptop without scrolling. The approved definition said "under the score". They were moved directly under the score badge (`f213c23`, [screenshot](screenshots/12-odds-under-score.png)) and deployed from `main`; the hosted acceptance check passed 30 of 30. Walks show no odds, as designed.

## Trends: hosted preview check (2026-10-14)
Sai added `DATABASE_URL` and `DB_POOL_MAX` to Vercel's Preview environment. `build-scores` was re-run from `feature/trends` ("Scored 158 neighbourhoods and 5748 street cells"), and a preview was deployed: https://uavert-pyu1rerod-sai-project.vercel.app (protected: open it while signed in to Vercel).

The preview sits behind Vercel's login, so `acceptance_check.py` ran through a local proxy that forwards each request with `vercel curl`:
- **Passed on the preview:** setup, 3, 4, 10, 10b, 11, odds-r2, odds-1, odds-3, odds-1b, **trends-2** (Yonge-Bay Corridor violent −38%, property −35%), **trends-3** (Toronto violent +10%, property +5%), **trends-2b**.
- **12** failed only on time (3.8 s against 2 s); the proxy adds about 3–4 s per request because it starts the Vercel CLI each time. Timed directly with `vercel curl`, the server answered in 0.22 s.
- The proxy then dropped the walking-route request, so the rest were checked directly: walk Union Station → Kensington 200 in 0.61 s (LineString, 2,840 m, 1 stand-out stretch); Mississauga 422 `outside_coverage`; "zzqqxx nowhere 12345" 404 `address_not_found`; Scarborough walk 422 `route_too_long` ("Those places are 17.6 km apart…"); `/rules.html` has the "Trends over time" section. Checks 15–51 (time of day, walks, rules) weren't re-run on the preview: that code is unchanged by trends and passed 33 of 33 locally on 2026-10-08.

**Merged (2026-10-14 13:07).** With Sai's approval ("yes sounds good i approve both"), `feature/trends` was merged into `main` (`c6b6084`). 238 tests passed; the push deployed production, and `acceptance_check.py` against https://uavert.vercel.app passed **33 of 33**. The daily refresh now keeps the trends.

**Odds percentage and "Risk score" label merged (2026-10-14 13:13).** With Sai's approval ("merge and i approve"), `feature/odds-percent` was merged into `main` (`3ac9994`). 238 tests passed; production redeployed and serves the new page code; `acceptance_check.py` against https://uavert.vercel.app passed **33 of 33**. Row 43 covers it.

**Time on the map, removed search, new colours merged (2026-10-15).** With Sai's approval ("yes"), migration 009 and `build-scores` ran on Neon `main` first ("Scored 158 neighbourhoods and 5748 street cells from 62,719 distinct crime events"; the site kept answering 200). Then `feature/time-map` was merged into `main` (`47970f8`). 250 tests passed; production redeployed and serves the new colours; `acceptance_check.py` against https://uavert.vercel.app passed **38 of 38**. The temporary Neon branch `time-map-check` was deleted. Rows 44–47 cover it.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
