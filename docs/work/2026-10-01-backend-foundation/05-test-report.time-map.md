# 5. Verify the work: time of day on the neighbourhood map; remove "Where I'm going"; new band colours

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Approved
**Verifies:** [01-03-time-map.md](01-03-time-map.md), criteria 29–35, built in [04-implementation.time-map.md](04-implementation.time-map.md).

## What this step is
This is the evidence that each new acceptance criterion is met, and that nothing that worked before has broken.

## What was done
- **Automated tests:** the full suite.
- **Real app:** started the app locally on the temporary Neon branch `time-map-check` (a copy of the real data, with migration 009 and a fresh `build-scores`). Ran `acceptance_check.py` against it, and drove the page in headless Edge with a scripted check.
- **Review:** went through the diff on correctness, readability, architecture, security and performance, and calculated colour contrast.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | "250 passed in 70.54s" (exit code 0) |
| Acceptance check, local app on real data | `python scripts/acceptance_check.py http://127.0.0.1:8011` | "38 of 38 checks passed" |
| Browser check (headless Edge, CDP) | scratch script, 18 checks | "18 of 18 browser checks passed" |
| Production before the change | `acceptance_check.py https://uavert.vercel.app` (start of session) | "33 of 33 checks passed" |

**Compared with the baseline:** 238 tests passed on `main` on 2026-10-14. There are now 250: 12 new, none removed, all passing.

**One intermittent failure.** In the first full run of this session, `test_meta_lists_data_date_and_collection_time_per_source` failed once. Only the summary line was kept, so the cause isn't known. It passed in the next three runs, two targeted and one full, with no code change in between. That test doesn't touch the hour code. It's recorded here in case it happens again.

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 29 | `hour` on both neighbourhood endpoints: unchanged without it; 422 outside 0–23; `time` object | Tests `test_neighbourhoods_without_hour_are_all_day` and `test_bad_hour_on_neighbourhoods_is_422` (24, −1 and "late", on both endpoints). Acceptance check 29: "no hour -> 'All day'; hour=2 -> '2 am'; hour=24 -> 422" | Passed |
| 30 | Score = all-day + median cell move, capped 0–100; unmoved cells; no cells | 5 unit tests in `tests/test_time_of_day.py`. One worked example: moves of +10, +20 and +40 give a median of +20, so 45 becomes 65. 90 + 30 is capped at 100, and the move is kept as 30. A neighbourhood with no cells keeps 37. | Passed |
| 31 | Real data: Yonge-Bay Corridor higher at 2 am than 2 pm; Guildwood moves ≤ 10 | Acceptance check 31: "crime all day / 2 am / 2 pm: Yonge-Bay Corridor [65, 100, 67], Guildwood [10, 10, 10]" | Passed |
| 32 | Reason at an hour, citing `activity_profile` and its dates | API tests for higher, lower and "about the same". Acceptance check 32: "Kensington-Chinatown 91 at 2 am: 'At 2 am: street blocks here typically score about 36 points higher than all day, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)'" | Passed |
| 33 | Map recolours; tooltip and panel at the hour; "(yearly)" headings; fast changes settle on the last | Browser checks:<br>- "Kensington-Chinatown recolours at 2 am: score 55, fill #e8792b → 91, #c62828"<br>- "tooltip names the hour: Kensington-Chinatown: 91 at 2 am"<br>- "fast changes settle on 11 pm: 0 differ" (changes 14 → 5 → 20 → 23 sent at once, compared with the API's 11 pm scores)<br>- "panel shows 'Showing: 2 am'"<br>- "odds and trend headings say yearly"<br>- "open neighbourhood re-runs on time change" | Passed |
| 34 | No "Where I'm going"; no console errors; a street click still works; walks work | Browser checks:<br>- headings are "When, Where I'm walking, Recent news, Data collected"<br>- "no console errors"<br>- the street click shows "Showing: 2 pm · Street level … 287 street incidents"<br>- the walk Union Station → Kensington Market shows "2.8 km · about 38 min"<br>Acceptance check 34 | Passed |
| 35 | Colours green, yellow, orange, red everywhere; readable badge text; still no "safe" | Browser legend: rgb(46,158,87), rgb(242,194,48), rgb(232,121,43), rgb(198,40,40); high badge rgb(198,40,40). Badge contrast: lower 3.42:1, moderate 7.98:1, elevated 5.31:1, high 5.62:1 (the badge number is 26 px bold, so large-text 3:1 applies). "no band is labelled safe". Dark-mode and phone screenshots `time-map-6` and `time-map-7`. | Passed |

Earlier criteria still hold: checks 1–28, odds and trends all pass in the same 38-of-38 run. Criterion 25 (City Hall street score higher at 2 am than at 2 pm) and 26 (the reason for the hour) are among them.

## Real-app checks
- **Data:** temporary branch `time-map-check`. `migrate` printed "Applied: 009_neighbourhood_by_hour.sql". `build-scores` printed "Scored 158 neighbourhoods and 5748 street cells from 62,719 distinct crime events."
- **API (all day / 2 am / 2 pm):**
  - Yonge-Bay Corridor: 65 / 100 / 67
  - Kensington-Chinatown: 55 / 91 / 43
  - Guildwood: 10 / 10 / 10
  - Bayview Woods-Steeles: 20 / 20 / 19
- **Speed:** `/api/v1/neighbourhoods?hour=2` returned 164,272 bytes in 1.08 s from this laptop, against 164,260 bytes and 1.37 s all-day. So the hour adds no cost.
- **Screenshots** ([screenshots/](screenshots/), all in dark mode because headless Edge followed Windows' dark theme):
  1. `time-map-1-all-day.png`: the city all day
  2. `time-map-2-at-2am.png`: downtown turns red at 2 am
  3. `time-map-3-neighbourhood-2am.png`: the Kensington-Chinatown panel at 2 am, 91, "High risk"
  4. `time-map-4-street-2pm.png`: a clicked street block
  5. `time-map-5-walk.png`: a walk
  6. `time-map-6-dark.png`: dark mode
  7. `time-map-7-phone-dark.png`: phone width, no sideways scrolling

## Code review findings

| # | Finding | Action |
|---|---|---|
| 1 | Error text would have become orange, at 2.9:1 contrast on white | Fixed: new `--error` colour (deviation 2 in the build record) |
| 2 | A clicked spot's neighbourhood line would stay all-day while the map shows the hour | Fixed: it follows the hour (deviation 1). Test updated. |
| 3 | **Deploy order:** code that reads the new columns would fail on a database without them | T5 runs migration 009 on Neon `main` **before** merging. The migration only adds columns that can be empty, so today's production code is unaffected by it. Until `build-scores` fills them, the API falls back to all-day scores. The hourly refresh workflow also runs `migrate` first. |
| 4 | **Security:** one new integer parameter, validated (422 outside 0–23). One form and its handler removed. All text still inserted with `textContent`, and tooltips still escaped. | No action |
| 5 | Acceptance check 29 first compared the all-day scores with themselves, so it proved nothing | Fixed before the final run: it now checks the `time` labels and the 422 |

## Could not verify
These go to your test list:
- **The hosted site:** production gets this only at T5, after your approval. The acceptance check will run against https://uavert.vercel.app then.
- **A real phone:** only a 390 px phone-sized window in headless Edge was checked (row 47).
- **Light mode on screen:** headless Edge followed Windows' dark theme. The light-mode colours were checked by calculation only (row 46).
- **Whether the changes make sense to you** (rows 44 and 46): your judgement.

## What happens next
Once you approve this and the build record:
1. run migration 009 and `build-scores` on Neon `main`
2. merge `feature/time-map` into `main`, which deploys
3. re-run the acceptance check against production

Rows 44–47 are added to your test list.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-15 14:33
- **User's response:** "yes" (to: approve the build and test records, and delete the temporary Neon branch once live)
- **Revisions before approval:** none
