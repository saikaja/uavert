# 5. Verify the work: map error fix, news dropdowns, and a walk scored by its typical block

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Verifies:** [01-03-panel-tidy.md](01-03-panel-tidy.md), criteria 52–55, built in [04-implementation.panel-tidy.md](04-implementation.panel-tidy.md).

## What this step is
This is the evidence for each criterion, and that the earlier parts of the page still work.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | "314 passed in 97.86s" (exit code 0) |
| Acceptance check, local app as `uavert_web` on the real data | `python scripts/acceptance_check.py http://127.0.0.1:8015` | "46 of 46 checks passed" |
| New browser check, before the change | scratch script | "2 of 13" (the bug reproduced: "routeLayer.bringToFront is not a function") |
| New browser check, after | scratch script | "13 of 13 browser checks passed" |
| Gauge browser check (regression) | scratch script | "14 of 14 browser checks passed" |
| Time-of-day browser check (regression) | scratch script | "17 of 18". The one difference is the old square-badge colour check, retired by the gauge (as recorded in [05-test-report.gauge.md](05-test-report.gauge.md)). |

**Compared with the baseline:** 311 tests on `main` before; now 314 (3 new), all passing. The old news browser check isn't rerun: it checked the layout these dropdowns replace. The new check covers the section.

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 52 | No error after moving the map with a walk shown; the walk stays on top | Walk shown, then 3 map moves. Status "(empty)", no console errors, route drawn above the blocks (position 264 against 262). Before the fix: the error, and the route under the blocks (159 against 264). | Passed |
| 53 | Five closed dropdowns with counts; full list when opened; no "Show all"; fits a phone | "five dropdowns in order"; "all closed on load"; "headings show counts"; "no 'Show all' buttons"; "opening a section shows all its items: visible 12, count 12"; "phone width: no sideways scrolling". Screenshots `tidy-1-news-closed.png` and `tidy-4-phone.png`. | Passed |
| 54 | `typical` in the API; the gauge shows it; worst block marked and named; Union → Kensington about 30 and 75 | Unit test `test_typical_cell_is_the_block_at_the_length_weighted_median`. API test `test_route_gives_its_typical_block_as_well_as_the_worst`. Browser: "gauge 30, typical 30, worst 75", "Worst block: 75 (high risk) · highlighted on the map", label "Risk score 30 out of 100: moderate risk, worst block 75: high risk". Acceptance check `tidy-54`. Screenshot `tidy-2-walk.png`. | Passed |
| 55 | Nothing lost about the worst block; a warning on the route still shows | Browser: "Worst block" heading with its reasons. API test `test_a_warning_on_the_route_still_shows_through_the_worst_block`: a walk ending in the seed's warning square gives `score` 90, alert 90, the "test heat warning" reason, and a lower typical. | Passed |

## Code review findings

| # | Finding | Action |
|---|---|---|
| 1 | Root cause of the error: a layer type without `bringToFront` | Fixed at the cause (the layer type), not by catching the error. Regression check added. |
| 2 | **My browser check scripts were reading a cached `app.js`** | Cache disabled in all check scripts. Production sends `must-revalidate` with an ETag (checked), so visitors aren't affected. |
| 3 | **Compatibility:** `/route-risks` | Fields added only. `score` is still the worst block, so existing API users see no change. |
| 4 | **Safety messaging:** the worst block stays visible four ways | Dial marker, named line, map highlight, its own reasons. A warning on the route is tested. |

## Could not verify
These go to your test list (row 54):
- **The hosted site:** after your approval.
- **A real phone.**
- **Whether the walk score now feels right to you.**

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
