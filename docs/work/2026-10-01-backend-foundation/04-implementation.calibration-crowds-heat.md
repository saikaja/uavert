# 4. Do the work (fairer scores, crowds, extreme heat): Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved

## What this step is
This document records building [01-03-calibration-crowds-heat.md](01-03-calibration-crowds-heat.md) (approved 2026-10-01 18:39), following the master-workflow build phase. Test results are in [05-test-report.calibration-crowds-heat.md](05-test-report.calibration-crowds-heat.md).

## What was done
Steps C1–C6 were built in order on `feature/backend-foundation`. Each step had tests written alongside it, was checked on the real data, and was committed. The full suite passes: **202 tests**.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| C1 | Fairer scale: 25 at a typical place, +20 per doubling (street, by hour, neighbourhood); a "× typical" reason; calmer first reason; walk `typical_score`; fairness check on the underlying rates | Done | `3d6de47` |
| C2 | Alert scores from Environment Canada's colours (yellow 40, orange 65, red 90; no colour: warning 65, watch or advisory 25) | Done | `afbde8a` |
| C3 | Extreme heat: 478 City cool spaces with weekly hours; heat alerts name the nearest space open at that time (or the chosen hour) | Done | `96680fa` |
| C4 | Crowds: 7 major venues (context only); large City events matched in the City calendar (35 within 1 km on their dates) | Done | `e12ab71` |
| C5 | Map and rules page: "Crowds" category, "mostly … ; worst block shown" on walks, "What the numbers mean" table, alert colours, heat and crowds explained | Done | `0b0eb4c` |
| C6 | `ingest daily` target; refresh workflow updated (also on `main`); production deploy; acceptance check extended; records | Done | `a9741ec`, `76a580f` (main), this commit |

## Results on the real data (2026-10-01)

**Scale:**

| | Before | After |
|---|---|---|
| Street blocks lower / moderate / elevated / high | 25 / 25 / 25 / 26 % | **49 / 28 / 16 / 7 %**, as simulated in the plan |
| Neighbourhoods lower / moderate / elevated / high | 40 per band | 76 / 76 / 6 / 0 |

- **Order of places:** 0 blocks reordered (sorted by the underlying value, no score goes down). The fairness check is unchanged at ρ −0.283 (income) / +0.236 (low-income share).

**The walk you asked about**, Union Station → 125 Blue Jays Way:

| | Before | After |
|---|---|---|
| Score | 80 "High" | **53 Elevated**, typical 35 Moderate |
| First reason | "3 homicides…" | "277 assaults within about 250 m in the last 12 months" |
| Second reason | | "About 2.7× the reported street crime per person of a typical Toronto block; busy area with about 1,589 people an hour on foot…" |
| At 2 pm / 10 pm | | 45 / 70 |

**Other places:**
- **City Hall:** 64 all day, 69 at 2 pm, **100 at 2 am**. Incidents continue overnight while about 11% of daytime foot traffic is out, an estimate from Bike Share data.
- **Union Station → Kensington Market:** **87 "High"**, the worst block, near Kensington. Most of that walk is lower.

**New data:**
- **Heat:** 478 cool spaces loaded (446 cooling locations, 12 cooling centres, 19 indoor pools, 1 wading pool).
- **Crowds:** **Nuit Blanche 2026** found on October 3 and 4, placed at City Hall, plus three of its sites. 8 large-event dates in the next 60 days. 7 venues placed (for example Rogers Centre, 39,150).
- **GitHub Actions run `36939044532`** (full): passed in 1 min 30 s, including `toronto_cool_spaces: 478` and `toronto_events: 26,402 calendar entries read, 8 large-event dates`.

## Files changed

| File | New / changed | Summary |
|---|---|---|
| `src/uavert/scoring/crime.py` | Changed | `relative_score`, `times_typical`, `POINTS_PER_DOUBLING` |
| `src/uavert/scoring/build.py` | Changed | Scale for neighbourhoods, streets and hours; reasons; fairness on rates |
| `src/uavert/scoring/route.py`, `api/routes/route_risks.py` | Changed | `typical_score` / `typical_band` |
| `src/uavert/scoring/alerts.py` | Changed | Colour-based levels |
| `src/uavert/scoring/heat.py`, `ingest/heat.py` | New | Opening hours, nearest open space, the reason; loader |
| `src/uavert/scoring/crowds.py`, `ingest/crowds.py` | New | Event and venue scoring; calendar matching and loader |
| `src/uavert/sources/toronto_open_data.py` | Changed | Cool spaces CSV, events feed |
| `src/uavert/api/live.py`, `api/timeofday.py`, `api/locate.py`, `api/routes/cells.py`, `api/routes/sources.py` | Changed | Heat and crowds at request time; the chosen hour is passed to opening-hours checks; new parameters |
| `src/uavert/scoring/combine.py` | Changed | `crowds` category |
| `src/uavert/ingest/steps.py`, `registry.py` | Changed | `heat`, `crowds` and `daily` targets; 3 new sources |
| `db/migrations/007_heat_and_crowds.sql` | New | `cool_spaces`, `venues`, `crowd_events` |
| `data/major_venues.csv`, `data/large_city_events.csv` | New | Reviewed lists with sources |
| `src/uavert/web/app.js`, `rules.html` | Changed | Crowds category, walk summary, rules sections |
| `.github/workflows/refresh.yml` (branch and `main`), `vercel.json` (`main` only) | Changed / new | Daily target; `main` doesn't auto-deploy until the merge |
| `scripts/acceptance_check.py` | Changed | Checks for criteria 40, 41, 44, 51 |
| tests (`test_scoring_core`, `test_build`, `test_route_rules`, `test_live`, `test_heat`, `test_crowds`, `api/test_heat_api`, `api/test_crowds_api`, `api/test_route_risks`, `api/conftest`) | New / changed | Criteria 40–51 |

## Deviations from the plan
1. **Criterion 42 (rank correlation 1.0).** Capping scores at 0 and 100 makes some ties, so the exact rank correlation of capped scores is slightly under 1.0. What's guaranteed and tested instead:
   - no place is ever reordered (0 inversions on the real data)
   - the fairness check now uses the underlying rates, so it is exactly unchanged
2. **Combined reason for streets.** The "× typical" comparison and the foot traffic are now one reason, so both fit within the two crime reasons shown.
3. **Crowd events from the real calendar** needed three filters that the plan didn't foresee, all found by checking the real data:
   - locations like "Various" are treated as missing (address search had placed "Various" in Alberta)
   - results outside Toronto fall back to the event's default location
   - non-featured spin-offs count only on the featured event's dates, which dropped a "Nuit Blanche Artist Meet and Greet" the day before
4. **`vercel.json` on `main`.** It turns off Git deploys from `main`, so the workflow could be updated there without replacing the live site. It will conflict with the branch's `vercel.json` at merge time; keep the branch version.
5. **The API test warning is now red.** It had been yellow; yellow is now moderate by design.

## Clean-up
New modules are small and pure, with ingestion kept separate. `pyflakes` reports no issues. No separate simplification pass was run for this round.

## Follow-up ideas
- **Night-time strength:** City Hall at 2 am scores 100, a large night effect driven by the Bike Share estimate. Consider capping how much "fewer people out" can multiply risk, or softening it with daytime foot-traffic counts for night-time areas.
- **Crowds:** game and concert schedules, with a licence-compatible source.
- **Cold:** extreme cold and warming centres.

## What happens next
Once this and the test report are approved, the phase 6 checklist ([06-e2e-signoff.md](06-e2e-signoff.md)) has new rows for these changes.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 19:16
- **User's response:** "approved and run and push to the vercel so i can test online"
- **Revisions before approval:** none
