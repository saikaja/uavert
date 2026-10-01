# 2. Review the design (revision 2): the downtown "busy street" fix

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval
**Revises:** [02-design.md](02-design.md) (approved 2026-10-01). Everything in that design stays as it is except the parts changed below.

## Why this revision
During the build (phase 4), live checks showed a problem with walking routes downtown.
- **What you see:** every block on the walk from Union Station to Kensington Market scores "high" (97–100). So does every block from City Hall to Yonge-Dundas Square.
- **Why it matters:** "Riskiest stretches" is meant to tell a walker which part of the route to watch. Here it returns the whole route as one stretch, so it says nothing useful downtown.
- **Cause:** street scores rank each block against the whole city. Downtown has far more reported incidents than anywhere else, partly because far more people are there. This is the "busy street" problem in the build plan's "Getting to street level" section.
- **Decision:** after seeing this, the user asked for the downtown issue to be tackled before phase 5.

## What was done
Three fixes were tested against the real scores in the database (5,748 cells, built 2026-10-01) and two real walking routes from OSRM.

| Option | Downtown cells "high" (65 cells within 1.5 km of City Hall) | Union Station → Kensington Market, cell by cell | Result |
|---|---|---|---|
| Current: rank against the whole city | 62 of 65 | 100, 98, 100, 99, 98, 97, 99, 99: all high | No difference between blocks |
| Blend: 50% city rank + 50% rank within the surrounding 1 km | 49 of 65 | 98, 82, 94, 84, 82, 70, 88, 88: 7 of 8 high | Small change; the score becomes harder to explain |
| Blend: 50% city rank + 50% rank within the neighbourhood | 39 of 65 | 95, 98, 80, 68, 74, 61, 96, 91: 5 of 8 high | Some separation, but the walk's overall score is still 98; scores change when a neighbourhood boundary is crossed |
| **Compare each block with its surrounding 1 km** (recommended) | unchanged | 6.9×, 2.8×, 4.5×, 1.9×, 1.5×, 0.8×, 2.2×, 2.5× the surrounding median | Clear separation: the Union Station block stands out most, and the Kensington end is below its surroundings |

City Hall → Yonge-Dundas Square, compared with the surrounding 1 km: 2.8×, 1.0×, 3.8×, 6.5×, 5.5×. The Yonge-Dundas end stands out.

## Approach
**Keep the score honest, and add a second measure that answers "which part of this walk stands out?"**

1. **The 0–100 score is unchanged.** It keeps the city-wide ranking with CSI weights. A downtown walk still says "high", because downtown does have the most reported crime in Toronto. Hiding that would be misleading.
2. **New measure: "compared with surroundings".** For every street cell, the score build adds a stored `vs_surroundings` value:
   - its value ÷ the median value of the cells within 6 rings, about 1 km
   - for example, 2.8 means about 2.8 times the reported street crime of the area around it
   - the reasons say: "About 2.8× the reported street crime of the surrounding 1 km"
3. **Riskiest stretches use this measure.**
   - The route is split into stretches, one per cell crossed (about 175 m each).
   - The 3 that stand out most from their surroundings are returned. Neighbouring picks join into one stretch.
   - Only stretches at least **1.5×** their surroundings count. If none qualifies, the response says "No stretch of this walk stands out from its surroundings" rather than highlighting something arbitrary.
   - Each stretch still shows its own 0–100 score, band and reasons.
4. **Busy-area context.** In about the top 10% of the city, the surrounding area itself is very busy: the median value within 1 km is in the city's top decile. Reasons for cells there add: "Busy area: incident counts here partly reflect large numbers of people." This makes the "busy street" effect visible instead of leaving people to guess.

**Unchanged:**
- the neighbourhood scores
- the rule that the highest category wins
- the bands, air quality, alerts and news
- every endpoint's path

## Changes

| File | New / changed | What changes |
|---|---|---|
| `db/migrations/003_cell_surroundings.sql` | New | `cell_scores`: add `vs_surroundings double precision` and `busy_area boolean` |
| `src/uavert/scoring/crime.py` | Changed | `surroundings_ratio(values, cell, ring)` and `busy_areas(...)` as pure functions |
| `src/uavert/scoring/build.py` | Changed | Computes and stores both measures; adds the two reasons |
| `src/uavert/scoring/route.py` | Changed | `standout_stretches(...)`: one stretch per cell, ranked by `vs_surroundings`, 1.5× minimum, neighbours joined |
| `src/uavert/api/routes/route_risks.py`, `cells.py` | Changed | Return the new fields (below) |
| `src/uavert/web/app.js` | Changed | Route panel: "Stretches that stand out" with "2.8× its surroundings"; cell tooltips show the ratio |
| `src/uavert/web/rules.html` | Changed | Explains "compared with surroundings" and the busy-area note |
| tests | Changed / new | See Test strategy |

## Contracts
Fields are added; nothing is removed or renamed, so `/api/v1` stays compatible.

- **`GET /api/v1/cells`:** each feature's properties gain `vs_surroundings` (number) and `busy_area` (boolean).
- **`GET /api/v1/risk-scores`:** `street` gains `vs_surroundings` and `busy_area`.
- **`GET /api/v1/route-risks`:**
  - each item in `riskiest_segments` gains `vs_surroundings`; the items are now ordered by how far they stand out
  - when no stretch reaches 1.5×, `riskiest_segments` is `[]` and a new field `segments_note` explains why
  - the top-level `score`, `band` and `reasons` are unchanged (the highest along the route)

## Review checklist

| Area | Finding |
|---|---|
| Edge cases and errors | **Empty surroundings:** if the median of a cell's surroundings is 0 (a quiet suburb), the ratio is undefined. In that case `vs_surroundings` is null and the cell can't be a stand-out stretch, so a single incident in an empty area isn't flagged. **Grid edges:** cells at the lake or the city boundary use only the neighbours that exist inside the grid. **Short routes:** a route crossing 1–2 cells can still return a stretch if it qualifies. |
| Security | No new inputs. |
| Performance | The ratio is computed once in the score build: 5,748 cells × 127 neighbours each, a few seconds. Requests just read a stored column. |
| Compatibility | Fields are only added. Saved data gains two columns, filled by the next `build-scores`. |
| Testability | The pure functions get hand-worked unit tests, and the route API test checks stretch ordering and the "none stands out" case. |

## Alternatives considered
1. **Blend a local rank into the 0–100 score.** Tested above: it changes little downtown and makes the score harder to explain ("half city, half local").
2. **Divide by foot traffic** (City of Toronto pedestrian counts at intersections, TTC station ridership). This is the most correct fix for the busy-street effect, because it estimates risk per person present. But the data is patchy outside downtown and needs its own loading and checking, which is not realistic before Tuesday. Recommended as the next step; the stored ratio doesn't block it.
3. **Fixed band thresholds instead of percentiles.** This is a separate issue: a quarter of the city is "high" by construction. It doesn't separate downtown blocks either, so it stays a follow-up.

## Risks

| Risk | How it's reduced |
|---|---|
| "6.9× its surroundings" next to Union Station still reflects crowds (a transit hub). | The busy-area note says so plainly. Foot-traffic normalisation is the real fix (alternative 2). |
| The 1.5× minimum and the 1 km radius are judgement calls. | Both are listed on the rules page and set as named constants. They are tuning items for the resident testing in the build plan. |

## Test strategy

| Check | How it will be tested |
|---|---|
| The ratio is the value ÷ the median of the surrounding cells | Unit test with hand-worked values; a zero median gives null |
| Busy areas are about the top 10% by surrounding median | Unit test on a made-up grid |
| Stretches are ranked by ratio, below 1.5× is excluded, neighbours are joined, at most 3 | Unit tests on a made-up route |
| "No stretch stands out" | API test: route through uniform cells → `riskiest_segments: []` with `segments_note` |
| The downtown walk now separates stretches | Live check, Union Station → Kensington Market: the overall score is still high, the stretches are ordered with the Union Station block first, and some blocks below 1.5× are not highlighted (reported in phase 5) |
| Existing acceptance criteria 6, 11, 12 and 13 still pass | The full test suite |

## What happens next
Once this revision is approved, I build it on the same branch, with tests, as an addition to phase 4. I then update `04-implementation.md` to record it and ask you to approve phase 4.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
