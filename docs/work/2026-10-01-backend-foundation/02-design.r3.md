# 2. Review the design (revision 3): adjusting street scores for foot traffic

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved
**Revises:** [02-design.md](02-design.md) and [02-design.r2.md](02-design.r2.md) (both approved 2026-10-01). Everything in them stays as it is except what is changed below.

## Why this revision
The user approved revision 2 (comparing each block with its surroundings) and added: "it should consider the general traffic in the area like u said as well". That was alternative 2 in revision 2: estimating risk per person present instead of counting raw incidents. This revision designs it, after checking which traffic data exists and testing it on the real scores.

## What was done
**Searched the City of Toronto Open Data portal** for pedestrian and ridership data on 2026-10-01.
- TTC ridership datasets: none has been updated since 2017–2020, so they were ruled out.
- The usable source is **"Traffic Volumes – Multimodal Intersection Turning Movement Counts"** (City of Toronto Transportation Services). It is refreshed daily; the files were updated 2026-09-30.
  - The **most-recent-count file** (`tmc_most_recent_summary_data`, 1.5 MB) has one row per counted location: **6,394 intersections** with coordinates, the count date and 8- or 14-hour totals of pedestrians, cyclists and vehicles.
  - **5,034 locations were counted in 2015 or later.** 1,516 of those were counted in 2025 or 2026.

**Coverage of the street grid,** using counts from 2015 or later:
- 91% of the 5,748 cells have a count within about 250 m (1 ring)
- 97% within about 500 m (2 rings)
- 99% within about 600 m (3 rings)

**Pedestrians per hour, median of counts within about 500 m:**

| Place | Pedestrians per hour |
|---|---|
| Union Station | 1,189 |
| Yonge-Dundas | 1,077 |
| Kensington | 493 |
| Jane & Finch | 102 |
| Leaside | 60 |
| Agincourt | 25 |

Citywide: median 40 per hour, 90th percentile 228.

**Tested on the real scores and two real downtown walks.** In every option, scores are ranked across the city as before; only the value being ranked changes.

| Option | Downtown cells "high" (65 within 1.5 km of City Hall) | Union Station → Kensington, cell by cell | City Hall → Yonge-Dundas | Elsewhere: Jane & Finch / Leaside / Agincourt |
|---|---|---|---|---|
| Today: raw incident counts | 62 | 100 98 100 99 98 97 99 99 | 100 97 100 100 100 | 59 / 86 / 83 |
| Fully per person (pedestrians, no floor below the city median) | 18 | 72 29 58 33 41 30 87 86 | 67 31 71 90 87 | 56 / 88 / 92 |
| **Per person, with a minimum of 100 pedestrians an hour** (recommended) | **38** | **87 53 78 57 64 54 95 94** | **84 55 87 96 95** | **62 / 89 / 86** |
| Per person, with a minimum of 228 an hour (90th percentile) | 52 | 96 76 91 79 83 77 98 98 | 94 77 95 99 98 | 60 / 87 / 84 |
| 50% counts + 50% per person | 51 | 94 76 89 78 81 76 97 96 | 92 76 94 98 98 | 60 / 88 / 84 |

**Reading the results:**
- **Fully per person:** separates downtown blocks best. But it pushes car-oriented suburban plazas to the top: only 1% of the 200 highest cells are downtown, and their median foot traffic is just 37 an hour. Intersection counts miss people in parking lots and plazas, so a small denominator inflates the rate. That is a measurement problem, not real risk.
- **Minimum of 100 an hour:** keeps most of the downtown separation (blocks range from 53 to 95). Suburban hot spots move only a few points from today.

## Approach
1. **New data source: City of Toronto intersection counts.**
   - Load the most-recent-count file into a new table, `foot_traffic_counts`: location, coordinates, H3 cell, count date, hours counted, pedestrians, cyclists, vehicles, `collected_at`.
   - Only counts from **2015 or later** are used.
   - Pedestrians per hour = total pedestrians ÷ hours counted (8 or 14).
   - The source records its data date (the newest count date) and its collection time, like every other source.
2. **Foot traffic estimate for each street cell:**
   - the median pedestrians per hour of counts within 1 ring (about 250 m)
   - if there are none, within 2 rings, then 3
   - otherwise the city median

   The estimate, the number of counts used and their date range are stored with the cell.
3. **Street crime score per person:**
   - `per_person = smoothed_value ÷ max(foot_traffic, 100)`
   - `crime_score` = the percentile rank of `per_person` across Toronto
   - The minimum of 100 an hour stops thinly counted areas from looking extreme.
   - Recency, the street-premises filter, the neighbouring-cell weighting and leaning toward the neighbourhood are unchanged. They all feed `smoothed_value` as before.
4. **Revision 2 builds on this:**
   - **Compared with surroundings:** `vs_surroundings` is computed on `per_person`, so "stands out" means stands out *for the number of people there*. Stretches still need to be at least 1.5× their surroundings.
   - **The busy-area note is now based on foot traffic** instead of revision 2's incident-volume proxy. A cell is busy when its foot traffic is at or above the city's 90th percentile (about 230 an hour). The note says: "Busy area: about 1,190 people an hour on foot nearby; this score allows for crowds."
5. **Reasons.** Each street score adds a foot traffic reason, for example: "About 1,190 people an hour on foot at nearby intersections (City of Toronto counts, 2019–2026)". It gives the source and the dates of the counts used.
6. **Neighbourhood scores are unchanged** (per resident, calendar 2025). Adjusting neighbourhoods for visitors is a separate follow-up.

## Changes

| File | New / changed | What changes |
|---|---|---|
| `db/migrations/003_foot_traffic.sql` | New | `foot_traffic_counts` table. `cell_scores` gains: `foot_traffic_per_hour`, `foot_traffic_counts_used`, `foot_traffic_first_date`, `foot_traffic_last_date`, `per_person_value`, `vs_surroundings`, `busy_area` |
| `src/uavert/sources/toronto_open_data.py` | New | Finds the file through the CKAN API by dataset and resource name, so a moved file still resolves; downloads and parses the CSV |
| `src/uavert/ingest/traffic.py`, `registry.py`, `cli.py` | New / changed | New source `toronto_tmc` (licence and attribution); `uavert ingest traffic`, also included in `ingest all` |
| `src/uavert/scoring/crime.py` | Changed | Pure functions: `foot_traffic_estimate`, `per_person`, `surroundings_ratio`, busy-area threshold |
| `src/uavert/scoring/build.py` | Changed | Computes and stores the new values; new reasons |
| `src/uavert/scoring/route.py`, `api/routes/route_risks.py` | Changed | Stretches that stand out (revision 2) |
| `src/uavert/api/routes/cells.py`, `api/locate.py` | Changed | New fields in responses |
| `src/uavert/web/app.js`, `rules.html` | Changed | Foot traffic and "compared with surroundings" in the panels and tooltips; rules page explains both |
| `scripts/compare_rankings.py` | Unchanged | Neighbourhood scores don't change |
| tests | New / changed | See Test strategy |

## Contracts
Fields are only added, so `/api/v1` stays compatible.

- **`GET /api/v1/cells`:** properties gain `foot_traffic_per_hour`, `vs_surroundings` and `busy_area`.
- **`GET /api/v1/risk-scores`:** `street` gains `foot_traffic_per_hour`, `foot_traffic_counts_used`, `foot_traffic_dates` (first and last count date), `vs_surroundings` and `busy_area`.
- **`GET /api/v1/route-risks`:** the revision 2 fields, plus `foot_traffic_per_hour` on each stretch.
- **`GET /api/v1/scoring-rules`:** `parameters` gains:
  - `foot_traffic_floor_per_hour: 100`
  - `foot_traffic_since: "2015-01-01"`
  - `busy_area_per_hour`
  - `standout_min_ratio: 1.5`
  - `surroundings_rings: 6`
- **`GET /api/v1/sources`:** lists `toronto_tmc` with its data date and collection time.

## Review checklist

| Area | Finding |
|---|---|
| Edge cases and errors | **No count within 600 m:** the city median is used (under 1% of cells), and the reason says "estimated". **Zero pedestrians in a count:** the floor applies. **8- or 14-hour counts:** both are normalised to per hour. **Download or parse fails:** the stored counts are kept and the failure is recorded (as for every source); scores keep the last estimate. **Surroundings median of 0:** the ratio is null and the cell is never a stand-out stretch. |
| Security | No new inputs. The CKAN download is limited to the known City host. |
| Performance | The file is 1.5 MB, loaded in about 2 seconds. Foot traffic and surroundings are computed in `build-scores` (seconds); requests read stored columns. |
| Compatibility | Fields are only added. **Street scores change for every cell; that is intended.** Neighbourhood scores don't change. |
| Testability | Pure functions get hand-worked tests. The parser is tested on a saved sample of the real file. The API tests check the new fields. |

## Alternatives considered
1. **TTC ridership:** the open datasets stopped updating in 2017–2020, and they cover stations only.
2. **Fully per person (no floor):** tested above. It moves car-oriented plazas to the top because pedestrian counts miss people in parking lots.
3. **Population or job density as a proxy for foot traffic:** less direct than real pedestrian counts, and it would need census data loaded.

## Risks

| Risk | How it's reduced |
|---|---|
| Counts are snapshots: one day, 8–14 hours, mostly weekdays, some from 2015–2021 (including the pandemic). | Only the most recent count per location is used, from 2015 on. The median of nearby counts dampens one-off days. The dates used are shown in every reason. |
| Intersection counts miss people in malls, parks and plazas. | The floor of 100 an hour. The limitation is listed on the rules page. |
| Night-time foot traffic is not counted, but incidents happen at all hours. | This is noted as a limitation; separate day and night scores are already a follow-up. |
| Licence: CKAN lists the dataset as "License not specified". | The City of Toronto Open Data portal publishes its datasets under the Open Government Licence – Toronto. Recorded as such, with attribution "Contains information licensed under the Open Government Licence – Toronto". **Confirm before public launch.** |
| The floor (100), the 1.5× minimum and the 1 km radius are judgement calls. | They are named constants, shown on the rules page, and tuning items for the resident testing. |

## Test strategy

| Check | How it will be tested |
|---|---|
| CSV parsing: per-hour normalisation, 2015 cutoff, missing coordinates | Unit tests on a saved 20-row sample of the real file |
| Foot traffic estimate: 1 ring, then 2 rings, then 3 rings, then city median | Unit test on a made-up grid |
| Per person uses the floor of 100 | Unit test with hand-worked values |
| Compared with surroundings; a zero median gives null | Unit test |
| Busy-area threshold (90th percentile) | Unit test |
| Stretches that stand out: ranked, below 1.5× excluded, neighbours joined, at most 3, and the "none stands out" note | Unit and API tests |
| New fields in cells, risk-scores and route-risks; `toronto_tmc` in sources with its dates | API tests |
| A failed traffic download keeps the stored counts | Test with a faked failure |
| The live downtown walk separates stretches | Live check of Union Station → Kensington Market: scores vary and stand-out stretches are listed with foot traffic (reported in phase 5) |
| Existing acceptance criteria still pass | Full test suite |

## What happens next
Once this is approved, I build revisions 2 and 3 together on the same branch, with tests, as an addition to phase 4. I then update `04-implementation.md` and ask you to approve phase 4.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 13:00
- **User's response:** "yes"
- **Revisions before approval:** none
