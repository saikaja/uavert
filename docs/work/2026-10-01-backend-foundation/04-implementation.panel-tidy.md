# 4. Do the work: map error fix, news dropdowns, and a walk scored by its typical block

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Builds:** [01-03-panel-tidy.md](01-03-panel-tidy.md) (approved 2026-10-15, "aprove a").

## What this step is
This records how the three approved changes were built.

## What was done
- **Branch:** `feature/panel-tidy`, from `main` at `f34cea3`. Steps T1–T4, each committed.
- **Test first:** a new browser check (13 checks) was written before any change. On the old code it gave **2 of 13**, and reproduced Sai's message exactly: "routeLayer.bringToFront is not a function", with the walk drawn under the street blocks (route at layer position 159, blocks at 264). After the changes: **13 of 13**.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | Bug fix: the walk is drawn in an `L.featureGroup`, which has `bringToFront` | "no error after moving the map with a walk shown"; "walk line drawn above the street blocks" (route 264 above blocks 262) | `570557d` |
| T2 | "News and patterns" as five `<details>` sections, closed, with counts; "Show all" removed | "Trending (2)", "Protests · last 2 days (4)", "Violent incidents · last 7 days (6)", "Property crime · last 60 days (12)", "Patterns in police reports (6)". All closed on load; opening "Property crime" shows all 12. | `fbeed93` |
| T3 | Walk headline = typical block: `route.typical_cell()`, `typical` in `/route-risks`; worst block marked on the dial (triangle), named under the title, with its own reasons; rules page | Union → Kensington: gauge **30 (moderate)**, "Worst block: 75 (high risk) · highlighted on the map", label "Risk score 30 out of 100: moderate risk, worst block 75: high risk". 1 unit test and 2 API tests (including a walk ending under the seed warning: worst 90 with the warning reason; typical lower). | `d6bc3bf` |
| T4 | Acceptance check `tidy-54`; E2E rows 6 and 30 reworded; row 54 | Local, as `uavert_web`: **46 of 46**. Full suite: **314 passed**. | `0ed49c9` |

## Files changed

| File | Change |
|---|---|
| `src/uavert/web/app.js` | `L.featureGroup` for the walk; `newsSection()` and `newsList()` replace `newsGroup()`; `loadNews()` builds five sections; `showScore(…, worst)`; `placeWorst()` and the marker in `gaugeSvg()`; `runRoute()` shows `typical` with the worst block |
| `src/uavert/web/index.html` | `#news-sections` container; `#score-worst` line |
| `src/uavert/web/style.css` | Section and summary styles; worst-block marker and line; old `.news-group` style removed |
| `src/uavert/web/rules.html` | How a walk is scored |
| `src/uavert/scoring/route.py` | `typical_cell()`; `typical_score()` now uses it (same result) |
| `src/uavert/api/routes/route_risks.py` | Adds `typical` (the median block's full score). `score`, `typical_score` and `typical_band` are unchanged. |
| `tests/test_route_rules.py`, `tests/api/test_route_risks.py` | Criteria 54–55 |
| `scripts/acceptance_check.py`, `06-e2e-signoff.md` | As in T4 |

## Deviations from the plan
None in behaviour. Two notes:
- **The worst-block marker** is hidden when the worst block equals the typical one (as planned), but the "Worst block" line still shows, so the reader always sees it.
- **My browser check scripts were serving cached files.** While checking the T1 fix, the headless browser kept an old `app.js` from an earlier run; its profile is reused, and the local server sends no caching header. All check scripts now turn the browser cache off.
  - **Earlier results still stand:** each earlier run's own checks tested features that only existed in the then-current code, so they did load fresh files.
  - **Production isn't affected:** it sends `Cache-Control: public, max-age=0, must-revalidate`, with an ETag.

## Clean-up
- **Removed:** `NEWS_SHOWN`, `newsGroup()` and the `.news-group` style.
- **Shared logic:** `typical_score()` reuses `typical_cell()`, so the median logic exists once.

## Follow-up ideas
None.

## What happens next
Once you approve this and [05-test-report.panel-tidy.md](05-test-report.panel-tidy.md), I merge into `main`, which deploys, and check production.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
