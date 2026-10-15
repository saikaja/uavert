# 1–3. Define, design and plan: time of day on the neighbourhood map; remove "Where I'm going"

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Approved
**Adds to:** [01-03-time-of-day.md](01-03-time-of-day.md), which listed "Neighbourhood colours stay all-day" as a follow-up. This document covers phases 1–3 in one, as the workflow allows for a contained addition.

## What this step is
This document agrees how the "When" setting will change the neighbourhood scores on the map, and how the "Where I'm going" section will be removed. One approval covers the definition, the design and the plan. No code is written before it.

## What was done
- **The request.** On 2026-10-15 Sai wrote: "i want the time to affect the map score as well and not just for the where im walking and i think we can get rid of the where im going section and just leave the where im walking".
- **What already changes with the time.** Read the code on `main` (commit `c18ef38`):
  - **Street hexagons** (zoomed in), clicking a hexagon, "Where I'm going" and "Where I'm walking" already use the chosen hour ([01-03-time-of-day.md](01-03-time-of-day.md)).
  - **Neighbourhood colours** and the neighbourhood panel do not. `/api/v1/neighbourhoods` has no `hour`, and the page says "Neighbourhood colours are all-day". This is the "map score" the request means: the map most people see before zooming in.
- **How neighbourhood scores work today.** They are crime per resident for 2025 (all reported crime, including indoors), ranked against a typical neighbourhood. Residents don't change by hour, so the per-resident measure alone can't show "fewer people around at night".
- **Measured the proposed method on the real data** (production database, 158 neighbourhoods, 5,748 street cells). For each neighbourhood I took how far its typical (median) street cell's score moves at each hour, compared with all day:

  | Hour | 2 am | 5 am | 8 am | 12 pm | 5 pm | 9 pm | 11 pm |
  |---|---|---|---|---|---|---|---|
  | Median move across neighbourhoods | +1 | −9 | −15 | −8 | 0 | +6.5 | +5.5 |
  | Range | −25 to +58 | −32 to +58 | −41 to +6 | −51 to +9 | −32 to +19 | −13 to +28.5 | −16 to +41 |

  Examples (all-day score, then 2 am / 2 pm / 8 pm):
  - Yonge-Bay Corridor: 65, then **100** (capped) / 67 / 72
  - Kensington-Chinatown: 55, then **91** / 35 / 60
  - Bayview Woods-Steeles: 20, then 25 / 22 / 30
  - Guildwood: 10, then 10 / 10 / 19

  So busy downtown areas, where incidents continue after the crowds leave, rise sharply at night. Quiet residential areas barely move, and mornings are lower almost everywhere. This matches what the street hexagons already show.
- **Checked "Where I'm going" before removing it.** The same API (`/api/v1/risk-scores`) also answers a **click on a street hexagon**, and `acceptance_check.py` uses it. Only the search box and its form go. The click and the API stay.

## Definition

### Goal
1. The "When" setting changes the whole map: neighbourhood colours, the neighbourhood panel and the street hexagons.
2. The panel is simpler: "When", then "Where I'm walking", with no "Where I'm going" section.

### In scope
- **Neighbourhood scores by hour:** 24 stored scores per neighbourhood, built from that neighbourhood's street-level scores at each hour (see the design).
- **API:** an optional `hour` on `/api/v1/neighbourhoods` and `/api/v1/neighbourhoods/{id}`, which works like it does on `/cells`.
- **Map:** changing "When" recolours the neighbourhoods. Clicking a neighbourhood shows its score at that hour, with a reason that explains the change.
- **Remove "Where I'm going":** the search box and its form handler. Clicking a hexagon still shows that spot's street score at the chosen hour.
- **Wording:** update the "When" note, the rules page and the README.
- **New band colours** (Sai, 2026-10-15): green for lower, yellow for moderate, orange for elevated (Sai chose orange over blue at approval) and red for high. They apply to the neighbourhoods, hexagons, score badge, category bars, legend and route stretches.

### Out of scope
These are follow-ups:
- **Odds per resident and trends** stay yearly figures. An hour doesn't apply to "1 in N residents a year". The panel says so.
- **The default stays "All day".**
- **Day of week:** still not covered.
- **The `/api/v1/risk-scores?address=` API** stays, for compatibility. Only the page's search box goes.

### Acceptance criteria (added to criteria 1–28)
29. `/api/v1/neighbourhoods` and `/api/v1/neighbourhoods/{id}` accept an optional `hour` (0–23):
    - without it, responses are exactly as today
    - an hour outside 0–23 returns 422 `validation_error`
    - both responses include the `time` object used by `/cells`
30. **Scoring.** A neighbourhood's crime score at hour h is its all-day score plus the median change of its street cells' scores at h, kept within 0–100. Unit tests with hand-worked numbers check:
    - a neighbourhood whose cells don't change keeps its score
    - capping at 0 and 100
    - a neighbourhood with no cells keeps its all-day score
31. **Live check on the real data.** Yonge-Bay Corridor scores higher at 2 am than at 2 pm. Guildwood moves by 10 points or less between those hours.
32. **Reason.** With an hour, the neighbourhood's first crime reason says how its typical street block changes at that hour and why. Example: "At 2 am: street-level risk here runs about 35 points above its all-day level, as incidents continue with few people out (estimated from Bike Share trips)". It cites `activity_profile` with its dates.
33. **Web map:**
    - changing "When" recolours the neighbourhoods
    - the tooltip and panel show the score at that hour, and the panel says "Showing: 2 am"
    - the odds and trend sections say they are yearly figures
    - a fast series of changes settles on the last choice, with no flicker back
34. **No "Where I'm going":**
    - the section is gone, and nothing on the page or in the browser console errors
    - clicking a hexagon still shows the street score at the chosen hour
    - "Where I'm walking" works as before
35. **Colours:**
    - every band colour on the map, legend, badge, bars and walk stretches is the new green, yellow, orange or red
    - badge text stays readable on each colour (contrast at least 3:1 for the large badge number), in light and dark mode
    - the bands keep their labels: "Lower reported risk", never "safe"

## Design

### Colours

| Band (score) | Old | New | Badge text |
|---|---|---|---|
| Lower reported risk (0–24) | pale yellow `#f7e3a3` | green `#2e9e57` | white |
| Moderate risk (25–49) | orange `#f3a65a` | yellow `#f2c230` | dark `#3a2e00` |
| Elevated risk (50–74) | red-orange `#d9562f` | orange `#e8792b` | dark `#3a1d00` |
| High risk (75–100) | dark red `#9e1b2c` | red `#c62828` | white |

- **One source of truth:** the colours are in `BANDS` in `app.js` and the `--band-*` variables in `style.css`. Both change together.
- **Walking route line:** stays dark blue `#1f4e79`. No band uses blue.
- **Error text:** keeps using `--band-elevated`, which is now orange.
- **Buttons and links:** keep the dark blue accent. They aren't on the map.

### Scoring (in `uavert build-scores`)
For each neighbourhood N and hour h:
1. `move_h = median over N's cells of (cell crime_score_by_hour[h] − cell crime_score)`
2. `crime_score_by_hour[h] = clamp(N.crime_score + round(move_h), 0, 100)`
3. Also store `move_by_hour` (24 values) for the reason.

**Why this method.** A cell's score is 25 + 20 × log2(its per-person value ÷ a typical block's). A shift of x points therefore means the block's crime per person out changes by 2^(x/20) at that hour. That holds whatever the starting point. So adding the typical block's shift carries that ratio onto the per-resident score without mixing the two measures' scales.

**Why the median.** One busy corner shouldn't move a whole neighbourhood.

**Where it's computed.** In `scoring/build.py`, after `cell_scores()`, in a new pure function `crime.neighbourhood_by_hour(hood_score, cell_moves)`. Nothing is computed per request.

### Storage
- **Migration `009_neighbourhood_by_hour.sql`:** adds `crime_score_by_hour smallint[]` and `move_by_hour real[]` to `neighbourhood_scores`. Both can be null, so the site keeps working until `build-scores` runs.
- **Production:** the migration and a `build-scores` run happen before the merge.

### API
- **Parameter:** `hour: int | None = Query(None, ge=0, le=23)` on both neighbourhood routes.
- **`timeofday.py`:** gains `neighbourhood_crime_at(row, hour, ctx)`, which mirrors `crime_at`. It returns the stored hourly score and the reason. With no hour, or no stored hours, it returns the all-day score.
- **Time-dependent parts:** `ctx.score(..., when=moment(hour, ctx))`, so crowds and events use that hour as they do for cells.
- **Response:** adds `time`, as on `/cells`. No existing field changes.
- **`/scoring-rules`:** gains one line describing the method.

### Web map
- **Neighbourhood layer:** `loadNeighbourhoods()` takes `hourParam()`. On a "When" change it re-styles the existing layer from the new scores, rather than redrawing it. A request counter, like the one for cells, drops stale answers. The payload is about 40 KB compressed, and production answered in 0.4 s.
- **Neighbourhood panel:**
  - re-runs on a time change, like other searches (it sets `lastSearch`)
  - shows "Showing: <time>"
  - the odds and trend headings get "(yearly)"
- **Removed:**
  - the "Where I'm going" card and the `dest-form` handler in `app.js`
  - `runDestination` keeps its name; it now serves map clicks only
  - the address-only `label` path (map zoom on search) goes
- **"When" note:** "Changes the map, street scores and walks. Air quality and alerts are always current."

### Review checklist

| Area | Finding |
|---|---|
| Edge cases | **Hour 0** works like any other hour. **Neighbourhood with no cells:** none today (every neighbourhood has cells), but the code keeps its all-day score. **Capped scores:** the reason states the move before capping. **Missing hourly scores** (migration not yet built): all-day is shown. |
| Security | Adds one validated integer parameter. One form is removed, so there's less user input. |
| Performance | The build adds 158 × 24 medians, which is negligible. Per request it picks one stored array element. Each time change re-fetches about 40 KB. |
| Compatibility | `/api/v1` responses without `hour` are unchanged. `/risk-scores?address=` remains. |
| Accessibility | Removing a form doesn't affect the remaining labels. The "When" note stays linked to the selector. |

### Alternatives considered
1. **Per resident, by when the neighbourhood's own incidents happen** (no foot traffic). This would make 2 am *lower* than the evening almost everywhere, because fewer incidents happen at 2 am. It would disagree with the street hexagons, and it misses the "fewer people around" effect the original time feature was built for. Rejected.
2. **Average of all cells' hourly scores**, replacing the per-resident score at each hour. The colours would then jump between two different measures when the time moves from "All day" to an hour. Rejected.
3. **Mean instead of median move.** A few busy corners would drag whole neighbourhoods. Rejected.

### Risks

| Risk | How it's reduced |
|---|---|
| Night foot traffic is estimated from Bike Share trips (as for streets). | The reason says "estimated from Bike Share trips". This is already on the rules page. |
| Downtown neighbourhoods reach 100 at night. This is a strong message. | It agrees with the street hexagons. The reason explains why. The rules page shows the method. |
| Orange and yellow are neighbours on the colour wheel and could be hard to tell apart. | The chosen orange `#e8792b` is clearly redder than the yellow `#f2c230`. This is checked on screenshots. |
| Green can read as "safe". | The label stays "Lower reported risk", and the disclaimer stays. |
| Removing "Where I'm going" takes away typing an address to check one spot. | Without the search box, the way to check one spot is to zoom in and click it. **Your call:** if you'd rather keep typed lookups, I can let "Where I'm walking" accept just a "To". Not planned unless you ask. |

## Plan
Branch `feature/time-map` from `main`. Each step has tests and a commit.

| # | What | Files | Tests | Done when |
|---|---|---|---|---|
| T1 | Neighbourhood scores by hour: pure function, build step, migration | `scoring/crime.py`, `scoring/build.py`, `db/migrations/009_neighbourhood_by_hour.sql` | Criterion 30, with hand-worked numbers | `build-scores` on the Neon `test` branch stores 24 scores per neighbourhood; criterion 31 holds there |
| T2 | API `hour` on both neighbourhood routes; reason; `time` object; scoring rules line | `api/routes/neighbourhoods.py`, `api/timeofday.py`, `api/routes/sources.py` (rules) | Criteria 29 and 32 (API tests: unchanged without hour, 422, score and reason at an hour) | Tests pass |
| T3 | Web: recolour on time change, panel re-runs, "(yearly)" labels; remove "Where I'm going"; note text; new band colours | `web/index.html`, `web/app.js`, `web/style.css`, `web/rules.html` | Criteria 33–35 in headless Edge, with screenshots (light and dark), a console-error check and a contrast calculation | Checks pass locally |
| T4 | README, acceptance check (Yonge-Bay 2 am > 2 pm), E2E rows: rows 5, 8, 15 and 16 change to use a map click or the walk, plus new rows 44–47 | `README.md`, `scripts/acceptance_check.py`, `06-e2e-signoff.md` | Full test suite; acceptance check against local | Everything passes |
| T5 | Production: run migration 009 and `build-scores` on Neon `main`, then merge and deploy after your approval of phases 4–5 | — | Acceptance check against https://uavert.vercel.app | All checks pass in production |

## What happens next
Once this is approved, I build T1–T4 on `feature/time-map` and write `04-implementation.time-map.md` and `05-test-report.time-map.md` for your approval. After that, T5 merges and deploys.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-15 14:15
- **User's response:** "approve use orange"
- **Revisions before approval:**
  1. 2026-10-15: Sai: "no i want the neighbourhood colors to change as well based on the time / and i also want to change the color scheme i want it to be green for lower risk, yellow for moderate, blue for elevated and red for the high risk". The neighbourhood colours by time were already the plan (criteria 29–33). Added the new band colours (scope, criterion 35, the "Colours" design section, risks, T3).
  2. At approval, Sai chose **orange instead of blue** for "elevated" (`#e8792b`, dark badge text, contrast 5.3:1). Because no band is blue any more, the route line stays blue and error text stays the elevated colour. The blue-specific risk was replaced with an orange-vs-yellow check.
