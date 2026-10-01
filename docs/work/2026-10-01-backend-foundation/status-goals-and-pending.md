# Uavert: goals and pending tasks

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **As of:** 2026-10-01 (end of day)  ·  **Demo:** Tuesday, October 6, 2026

This page is a snapshot of where the project stands, so work can resume from here. The phase documents listed in [README.md](README.md) are the formal record.

## Goals

### The main goal
Build a small web-app version of Uavert, a Toronto risk map, to show your boss on **Tuesday, October 6, 2026**. It sits on a backend that can grow to cover other regions, and later the world, without being rebuilt.

### What you asked for, and where it stands

| # | Goal | Status |
|---|---|---|
| 1 | Backend foundation: Neon Postgres (PostGIS + H3), Python ingestion, scoring engine, FastAPI, simple web map | Done |
| 2 | Crime weighted with the Statistics Canada Crime Severity Index (2009 weights) | Done |
| 3 | Street-level scores (H3 res-9 hexagons), not only neighbourhoods | Done |
| 4 | Ratings out of 100 for a destination ("Where I'm going") and a walking route ("Where I'm walking") | Done |
| 5 | News and protest signals that can raise the risk | Done (CBC + GDELT, marked unverified) |
| 6 | Track the date every piece of data was collected | Done (`as_of` and `collected_at` on every source and reason) |
| 7 | Fix the downtown issue (busy areas looked worse than they are) | Done (design r2) |
| 8 | Allow for general foot traffic | Done (design r3: crime per person on foot) |
| 9 | Time of day: pick an hour, and late at night can score higher | Done |
| 10 | Make it more solid: GitHub backup, saved lookups, automatic refresh, fairness check, homicide smoothing | Done |
| 11 | Host on Vercel from a private GitHub repository | Done: https://uavert.vercel.app (public link), repository `saikaja/uavert` (private) |
| 12 | Expand to the rest of the GTA | Researched and parked: police data licences block it (see [gta-expansion-notes.md](gta-expansion-notes.md)) |
| 13 | Fairer, less harsh ratings | Done: the walk Union Station → 125 Blue Jays Way went from 80–84 "High" to 53 "Elevated" (typical 35) |
| 14 | Big crowds and events (major venues + City festivals) | Done |
| 15 | Extreme heat (alerts name the nearest open cool space) | Done |
| 16 | Tools: graphify and agent skills installed; ponytail removed; one master-workflow skill | Done (OmniRoute skipped, by your choice) |

### Ground rules you set
- **Higher score = riskier.** Nothing is ever labelled "safe"; the lowest band is "Lower reported risk".
- **Stack:** Neon Postgres, Python + FastAPI, backend plus a web map.
- **Everything by Tuesday.**
- **Public Vercel link** for the demo.
- **GTA, when it happens:** rank places within each region, not across regions.

## Pending tasks

### 1. Your approvals (needed next)
- [ ] Approve [04-implementation.calibration-crowds-heat.md](04-implementation.calibration-crowds-heat.md), the build record for fairer scores, crowds and heat.
- [ ] Approve [05-test-report.calibration-crowds-heat.md](05-test-report.calibration-crowds-heat.md), its test report (202 tests passing, 26 of 26 live checks local and hosted).

### 2. Your end-to-end testing (rows 1–34 in [06-e2e-signoff.md](06-e2e-signoff.md))
All 34 rows are "Not tested". The ones that matter most:

| Row | What | When |
|---|---|---|
| 30 | Your walk, Union Station → 125 Blue Jays Way: does about **53 Elevated** ("mostly moderate (35)") feel right now? | Any time |
| 23 | The hosted site on laptop **and phone**: repeat rows 2, 5, 6 and 7 | Before the demo |
| 22 | Is the StatCan-weighted ranking acceptable to show? ([csi-vs-demo-ranking.md](csi-vs-demo-ranking.md)) | Before the demo |
| 33 | Nuit Blanche: search `100 Queen St W` and check the Crowds bar shows 35 | **Saturday, October 3, evening** only |
| 27–28 | Automatic refresh shows green ticks on GitHub Actions; "collected" times are recent | After a few hours |
| 34 | Heat warning reason | Only during a real heat alert (summer); can stay "Not tested" |

Reply with your results (for example "all passed" or "row 6 failed: …"). Failures get fixed, re-tested and handed back as "Round 2".

### 3. Close-out after you sign off (I'll ask before each step)
- [ ] Merge `feature/backend-foundation` into `main`. At the conflict on `vercel.json`, keep the branch's version, which turns deploys from `main` back on.
- [ ] Delete the GitHub Actions variable `DATA_BRANCH`. After the merge, the refresh runs from `main`.
- [ ] Optionally delete the empty `fresh_check` database on the Neon test branch.

### 4. Offered, not yet requested
- A short demo deck for Tuesday.
- Draft permission emails to York, Durham and Peel police for GTA data.

### 5. Follow-up ideas (not started)
- **Soften the night effect.** City Hall scores 100 at 2 am, and Union Station → Kensington scores 87 because of one block. Option: cap how much "fewer people out" can multiply the risk.
- **Crowds:** game and concert schedules, from a source whose licence allows it.
- **Extreme cold** and warming centres.
- **News:** a licensed news source. The CBC feed is for personal, non-commercial use, a risk on the public link that you accepted.
- **Traffic danger:** KSI (killed or seriously injured) collision data.
- **"Help nearby":** places to get help, from OpenStreetMap.

## Things to keep in mind
- **Don't push to `main` before the merge.** It's set not to deploy, but the merge is the planned switch-over.
- **Secrets stay put.** The database URL lives only in `.env`, the GitHub secret and the Vercel environment, and is never committed.
- **Neon:** deleting anything needs your permission first.
- **GTA data:** York police data prohibits commercial use; Durham and Peel need permission.
- **Running locally:** `.\.venv\Scripts\python.exe -m uavert serve`, then open http://localhost:8000. The `uavert.exe` launcher is blocked by Smart App Control.
