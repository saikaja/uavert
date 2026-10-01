# 4. Do the work (time of day): Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval

## What this step is
This document records building the time-of-day addition, which was defined, designed and planned in [01-03-time-of-day.md](01-03-time-of-day.md) (approved 2026-10-01 13:21). It sits alongside the approved [04-implementation.md](04-implementation.md), which is unchanged.

## What was done
Built after phase 4 was approved, at the user's request, on the same branch. Steps T1–T5 of that document's plan:

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | People out by hour: `data/activity_by_hour.csv` (City counts 6 am–7 pm; Bike Share 2025 at night, scaled by 1.005), `activity_by_hour` table, `activity_profile` source | Done | `19fc200` |
| T2 | Street crime score for each of the 24 hours (3-hour window, leaning toward the city pattern, per person at that hour, ranked across all blocks and hours) | Done | `5372bc9`, fix `c684ce8` |
| T3 | Optional `hour` on cells, risk-scores and route-risks; `time` object; a reason for the hour | Done | `2aaf114` |
| T4 | "When" selector on the map; time-of-day section on the rules page | Done | `660fcb2` |
| T5 | README and this addendum | Done | this commit |

**Live results** (real data, 2026-10-01):

| Check | Result |
|---|---|
| City Hall street score | all day 84; 2 pm 87; 10 pm 94; 2 am 99 (criterion 25: 2 am > 2 pm) |
| Kensington | 77 at 2 pm → 100 at 2 am: its late-night incidents run at 1.6× its average |
| Union Station → Kensington walk | 84 at 2 pm → 100 at 2 am |
| Reason at 2 am | "At 2 am: incidents near here run at about 0.8× this block's average, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)" |

**Tests:** 142 pass, including new unit tests for:
- the time window and its wrap past midnight
- the hourly shares, with untimed incidents spread evenly
- leaning toward the city pattern
- intensity
- per person at each hour
- the build producing higher scores at an emptier hour
- the hourly profile file

And API tests for:
- "no hour means unchanged"
- scores and reasons at 2 am and 2 pm
- cells and route at an hour
- 422 for bad hours

**Deviations:**
1. **Untimed incidents** follow the design (homicides count evenly across the day), but incidents with 00:00 times are kept as midnight, as noted in the design's risks.
2. **Display fix:** while checking the map I found that whole-day dates (stored as midnight UTC) displayed as the evening before in Toronto time, for example "Dec 30, 2025, 7:00 p.m." instead of "Dec 31, 2025". This affected every source, not only the new one. Both pages now show such dates as dates.
3. **Wording for busy hours:** above the daytime average, the hour reason says "foot traffic is about 1.1× the daytime average" rather than "107% of daytime foot traffic".
4. **Process slip:** commit `5372bc9` was made while one new test was failing. My command printed only the last line of the pytest output, and the failure was in the line above. The test's second assertion was wrong, not the code. It was fixed in `c684ce8`, and since then each commit runs the suite and checks its exit code.

**Screenshots:** [03-map-with-time-selector.png](screenshots/03-map-with-time-selector.png), [04-rules-page-time.png](screenshots/04-rules-page-time.png).

**Follow-ups:**
- day of week and weekends
- night-only "stand out" stretches
- time-aware neighbourhood colours
- intersection counts at night, if the City ever publishes them

## What happens next
Once this is approved, phase 5 (test the work) covers everything:
- the original build
- revisions 2 and 3
- the time-of-day addition, including acceptance criteria 21–28

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
