# 4. Do the work: time of day on the neighbourhood map; remove "Where I'm going"; new band colours

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Builds:** [01-03-time-map.md](01-03-time-map.md) (approved 2026-10-15 14:15, "approve use orange").

## What this step is
This records how the approved plan was built, step by step, with the evidence from real data.

## What was done
- **Branch:** `feature/time-map`, from `main` at `c18ef38`.
- **Steps:** T1 to T4, each with tests and a commit. T5 (production) waits for your approval of this document and the test report.
- **Approach:** the scoring tests were written first and failed (4 failed, 7 passed) before the function existed.
- **Real data:** the Neon `test` branch is used only by the automated tests and has no crime data, so `build-scores` couldn't run there. To check on real data, I made a temporary Neon branch, `time-map-check` (`br-noisy-shape-b549681x`), copied from `main`. I ran migration 009 and `build-scores` on it, then ran the local app against it. Production (`main`) has not been touched.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | Neighbourhood scores by hour: `crime.neighbourhood_by_hour`, `build.add_hours`, migration 009 | 5 unit tests. A read-only build from the real data took 5.6 s for 158 neighbourhoods and 5,748 cells; every neighbourhood has 24 hourly scores. Yonge-Bay Corridor: all day 65, 2 am **100**, 2 pm 67. Guildwood: 10 / 10 / 10. | `fa9b677` |
| T2 | `hour` on `/neighbourhoods` and `/neighbourhoods/{id}`; reason; `time` object; scoring-rules line | 6 new API tests (plus 2 more parameter cases), and the seed data has hourly neighbourhood scores. With the real data, Kensington-Chinatown at 2 am: 91, "At 2 am: street blocks here typically score about 36 points higher than all day, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)". | `86d1c12` |
| T3 | Web: neighbourhoods recolour on a time change, the panel re-runs, "(yearly)" headings; "Where I'm going" removed; new band colours; rules page | 18 of 18 headless Edge checks passed against the real data, with screenshots in [screenshots/](screenshots/) (`time-map-1` to `time-map-7`) | `a74d9a3` |
| T4 | README; acceptance checks 29, 31, 32, 34 and 35; E2E rows reworded, plus new rows 44–47 | Acceptance check against the local app on the copied data: **38 of 38** | `12c992e` |
| T5 | Production: migration 009 and `build-scores` on Neon `main`, merge, deploy | **Not done.** Waits for your approval. | — |

## Files changed

| File | New / changed | Summary |
|---|---|---|
| `db/migrations/009_neighbourhood_by_hour.sql` | New | Adds `crime_score_by_hour smallint[]` and `move_by_hour real[]` to `neighbourhood_scores`. Both can be null. |
| `src/uavert/scoring/crime.py` | Changed | `neighbourhood_by_hour()`: the all-day score plus the median move of the cells, capped to 0–100. Cells without hourly scores are left out; a neighbourhood with no cells keeps its all-day score. |
| `src/uavert/scoring/build.py` | Changed | `add_hours()` runs after `cell_scores()`, and the neighbourhood insert stores the two new columns. |
| `src/uavert/api/timeofday.py` | Changed | `neighbourhood_crime_at()` returns the score for an hour and its reason. The shared reason ending (people out, and the source) moved into `_hour_reason()`, which `crime_at()` also uses; its text is unchanged. |
| `src/uavert/api/routes/neighbourhoods.py` | Changed | Optional `hour`; scores and live conditions at that hour; `time` in the response. |
| `src/uavert/api/locate.py` | Changed | A clicked point's neighbourhood score also follows the hour (see the deviations). |
| `src/uavert/api/routes/sources.py` | Changed | `/scoring-rules` describes the method in `neighbourhood_by_hour`. |
| `src/uavert/web/app.js` | Changed | New band colours. Neighbourhoods reload and recolour in place on a "When" change, with a request counter so stale answers are dropped. The tooltip shows "… at 2 am". The neighbourhood panel shows "Showing: …" and re-runs on a time change. Odds and trend headings say "(yearly)". The address search handler is removed. |
| `src/uavert/web/index.html` | Changed | "Where I'm going" card removed; new "When" note. |
| `src/uavert/web/style.css` | Changed | New `--band-*` colours, badge text colours and a new `--error` colour. |
| `src/uavert/web/rules.html` | Changed | The time-of-day section says neighbourhoods follow the hour, and explains how. |
| `README.md` | Changed | Time of day and endpoint descriptions. |
| `scripts/acceptance_check.py` | Changed | Checks 29, 31, 32, 34 and 35. |
| `tests/test_time_of_day.py`, `tests/api/test_time_of_day_api.py`, `tests/api/conftest.py` | Changed | New tests and seed data. One existing assertion changed on purpose: "neighbourhood colours stay all-day" is now "the neighbourhood follows the hour". |
| `06-e2e-signoff.md` | Changed | Rows 1, 5, 10, 15 and 16 reworded; rows 44–47 added; a note that address searches become map clicks. |

## Deviations from the plan
1. **A clicked spot's neighbourhood line follows the hour too.**
   - The plan named only the two neighbourhood endpoints. But the panel for a clicked street block also shows "Neighbourhood: … score", from `/risk-scores`.
   - Leaving that all-day would show two different scores for the same neighbourhood at 2 am, which goes against the goal ("the 'When' setting changes the whole map").
   - It's a small change in `locate.py`, and one existing test was updated.
2. **Error text uses a new red, `--error`, rather than staying orange.**
   - At approval the plan said error text "keeps using `--band-elevated`, which is now orange". But the new orange on white is only 2.9:1, too faint for small text.
   - The new `--error` is `#c62828` in light mode (5.6:1) and `#ff7b72` in dark mode (6.4:1). The old error colour was 3.95:1, so this is also an improvement on before.
3. **Real-data checks ran on a temporary Neon branch,** not the Neon `test` branch, which has no crime data (see "What was done").
   - **It still exists:** `time-map-check` (`br-noisy-shape-b549681x`). Deleting it needs your OK.

## Clean-up
I reviewed the whole diff (251 lines added, 83 removed across 15 code files) and made no further changes.
- Shared code has one home: the "people out at this hour" sentence is `_hour_reason()`, and the neighbourhood fill opacity is `hoodFill()`.
- No debug code or unused functions remain. The `label` argument and the zoom-to-address code went with the search box.

## Follow-up ideas
- **One-spot lookups by typing:** let "Where I'm walking" accept only a "To", to check one place without a walk.
- **Band colour swatches** on the "How scores work" Bands table.
- **The walk's dark blue line** is less distinct over green blocks (screenshot `time-map-7`). If you find it hard to see, a white outline would help.

## What happens next
Once you approve, the test report ([05-test-report.time-map.md](05-test-report.time-map.md)) covers the checks. Then T5:
1. run migration 009 and `build-scores` on Neon `main`
2. merge `feature/time-map` into `main`, which deploys production
3. re-run the acceptance check against https://uavert.vercel.app

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
