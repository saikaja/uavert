# 1–3. Define, design and plan: time of day

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved
**Adds to:** [01-definition.md](01-definition.md) (scope and acceptance criteria), [02-design.md](02-design.md) with revisions [r2](02-design.r2.md) and [r3](02-design.r3.md), and [03-plan.md](03-plan.md). It covers phases 1–3 in one document, as the workflow allows for a contained addition.

## What this step is
This document agrees what the time-of-day feature does, how it is built and in what order. One approval covers all three; no code is written before it.

## What was done
- **The request.** On 2026-10-01, when approving phase 4, the user asked: "add a time feature where the later in the night someone would want to select the time and that would also affect the safety score". The original definition listed separate day and night scores as out of scope, so this is a scope addition.
- **When incidents happen.** Checked the stored incidents' times: street incidents in the last 12 months (outside, transit or commercial, plus shootings).
  - **Midnight:** 5.4%. Part of this is probably incidents with an unknown time recorded as 00:00.
  - **Overnight:** about 3–4% per hour from 1 am to 4 am, falling to 1.8% at 6 am.
  - **Daytime:** rising to 4–5% per hour from noon.
  - **Evening:** about 5.5–5.9% per hour from 5 pm to 10 pm.
  - **Homicides** have a date but no time in the Toronto Police data.
- **How many people are out at each hour.** Looked for data on how foot traffic changes through the day.
  - **City of Toronto 15-minute intersection counts**, 2020–2029 file, 361,443 rows, downloaded 2026-10-01. Using the 3,532 counts that ran a full 14 hours, the hourly pattern of pedestrians relative to the 6 am–8 pm average is:

    | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 |
    |---|---|---|---|---|---|---|---|---|---|---|---|---|---|
    | 0.20 | 0.44 | 1.00 | 0.82 | 0.73 | 0.89 | 1.16 | 1.07 | 1.07 | 1.28 | 1.34 | 1.60 | 1.34 | 1.07 |

    **There are no counts from 8 pm to 6 am.**
  - **Bike Share Toronto ridership 2025:** 7,812,520 trips with start times, around the clock, downloaded 2026-10-01. Relative to the same daytime average, the hourly pattern is:

    | Hour | 20 | 21 | 22 | 23 | 00 | 01 | 02 | 03 | 04 | 05 |
    |---|---|---|---|---|---|---|---|---|---|---|
    | Bike Share | 0.87 | 0.67 | 0.53 | 0.40 | 0.24 | 0.15 | 0.11 | 0.06 | 0.04 | 0.09 |

    For 6 am–7 pm it tracks the pedestrian counts closely: 0.26 against 0.20 at 6 am, 1.83 against 1.60 at 5 pm, 1.17 against 1.07 at 7 pm.
  - Bike Share is therefore a reasonable, data-based way to estimate the night-time hours that the pedestrian counts miss. It is still an estimate, and it is labelled as one.

## Definition

### Goal
Let a person choose the time they'll be somewhere or walking, and see how the risk changes. The later at night, the fewer people are around, and the score reflects that.

### In scope
- **Time selector:** "All day" (today's scores), "Now" (the current Toronto hour) or any hour from 12 am to 11 pm.
- **Street level only:** the selected hour changes the **street-level** crime score for:
  - street cells on the map
  - "Where I'm going"
  - "Where I'm walking"
- **Reasons** explain the time effect and its data sources.

### Out of scope
These are follow-ups:
- **Neighbourhood colours** stay all-day.
- **Day of week**, weekends and holidays.
- **"Stretches that stand out"** still compares blocks over the whole day. Night-only hot spots are a follow-up.
- **Air quality, alerts and news** always show current conditions, whatever hour is chosen. The response says so.

### Acceptance criteria (added to the 20 in 01-definition.md)

**API**
21. `/api/v1/cells`, `/api/v1/risk-scores` and `/api/v1/route-risks` accept an optional `hour` (0–23):
    - without it, responses are exactly as today ("All day")
    - an hour outside 0–23 returns 422 `validation_error`

**Scoring**
22. With `hour`, the street crime score reflects incidents around that hour and the people out at that hour. A unit test checks that when activity drops, the same incident level gives a higher score.
23. A block with few nearby incidents follows Toronto's overall pattern by hour instead of its own handful of times. A unit test checks this.
24. Incidents with no recorded time (homicides) count evenly across the day.
25. A live check on the real data: the street score for City Hall at 2 am is higher than at 2 pm.

**Explanation and data dates**
26. Each time-specific street score includes a reason. It names:
    - how incidents nearby at that time compare with the block's average
    - roughly how much foot traffic there is compared with daytime
    - whether that figure is measured (City counts) or estimated (Bike Share)
27. The hourly activity table records its sources and retrieval dates, and appears in `/api/v1/sources` with its data date and collection time.

**Web map**
28. The web map has a time selector. Changing it updates the street layer and re-runs the current destination or route. The panel says which time is shown, and that air quality and alerts are current.

## Design

### Data
- **New reference file: `data/activity_by_hour.csv`.** It has 24 rows: hour, `pedestrian_factor` (6 am–7 pm, measured), `bikeshare_factor`, `factor_used` and `basis` (measured or estimated). The header lines record both sources, the files used and the retrieval date (2026-10-01).
  - **Measured hours (6 am–7 pm):** `factor_used` is the pedestrian factor.
  - **Other hours:** the Bike Share factor × the average ratio of pedestrians to Bike Share over 6 am–7 pm. This lines the two sources up where they overlap.
  - The factors are relative to the 6 am–8 pm average. That matches the foot traffic estimates, which are averages over counted daytime hours.
- **`scripts/build_activity_profile.py`** regenerates the file from the City's raw files: about 315 MB of downloads, run rarely. The app reads the small CSV.
- **`uavert ingest reference`** loads the CSV into a new `activity_by_hour` table, with `collected_at`, under a new source, `activity_profile`. That source records its data date (2025-12-31, the last day of the Bike Share year) and its collection time.

### Scoring, for each street cell and each hour h

1. **Time window:** h−1 to h+1 (3 hours, wrapping past midnight), to smooth over sparse data.
2. **Share of incidents in the window:**
   - **Cell share:** the cell's nearby street incidents (the cell plus 1 ring, recency weighted, with known times) that fall in the window. Incidents with no time count 3/24 in every window.
   - **Leaning toward the city pattern:** `share = (n × cell_share + 10 × city_share) ÷ (n + 10)`, so a cell with few incidents follows the city's pattern.
   - **Intensity:** `intensity = share ÷ (3/24)`. 1.0 means an average hour for that block; 2.0 means twice the average.
3. **Incident value at that hour:** `value_h = smoothed_value × intensity`.
4. **Foot traffic at that hour:** `foot_h = foot_traffic_estimate × factor_used(h)`.
5. **Per person at that hour:** `per_person_h = value_h ÷ max(foot_h, 100)`. The same floor of 100 as revision 3.
6. **Score at that hour:** the percentile rank of `per_person_h` across **all cells and all 24 hours together**. That way a quiet 3 am ranks against a busy 3 pm, and later, emptier hours score higher where incidents continue.
7. **Storage:** `cell_scores.crime_score_by_hour smallint[24]`, plus `intensity_by_hour real[24]` for the reasons. Neighbourhood scores and the all-day street score are unchanged.

**Reason added when an hour is chosen.** Example: "At 2 am: incidents near here run at about 1.4× this block's average, and about 11% of daytime foot traffic is out (estimated from Bike Share trips)". It cites the `tps_mci` and `activity_profile` sources and their dates.

### API contract (fields added only; `/api/v1` stays compatible)
- **`hour`:** optional on `/cells`, `/risk-scores` and `/route-risks`; whole number from 0 to 23.
- **`time` object** in the response data:
  - `{"hour": 2, "label": "2 am", "window": "1 am-4 am"}` when an hour is chosen
  - `{"hour": null, "label": "All day"}` otherwise
  - a `note`: "Air quality, alerts and news show current conditions."
- **Street scores at an hour:** `categories.crime` and the combined score use the score for that hour. The route score is the highest cell score at that hour.
- **`/scoring-rules`:** gains `activity_by_hour` (the 24 factors and their basis) and the time window settings.

### Web map
- **Selector:** a "When" control at the top of the panel: All day, Now (shown with the current hour), then 12 am … 11 pm.
- **On change:** reload the street layer and re-run the last destination or route search.
- **Labels:** the details panel shows "Showing: 2 am (street level; neighbourhood colours are all-day)".

### Review checklist

| Area | Finding |
|---|---|
| Edge cases | **Wrap-around:** at hour 0 the window is 11 pm–1 am. **No timed incidents nearby:** the cell follows the city pattern. **Midnight spike:** incidents recorded at 00:00 may include unknown times. The 3-hour window and leaning toward the city pattern dampen this; it is listed as a limitation. **"Now"** uses the Toronto time zone. |
| Security | One new integer parameter, validated. |
| Performance | `build-scores`: 5,748 cells × 24 hours is about 138,000 values, a few seconds. Requests read the stored arrays and pick one element; nothing is computed at request time. |
| Compatibility | Without `hour`, every response is unchanged. Two new columns and one new table, filled by `ingest reference` and `build-scores`. |
| Testability | Window, intensity, leaning and per-person-by-hour are pure functions with hand-worked tests; API tests cover the `hour` parameter. |

### Alternatives considered
1. **Scale the score by a citywide night multiplier.** Simpler, but it ignores where the incidents happen at night (bar districts vs residential streets). Rejected.
2. **Rank within each hour separately.** This would erase the day/night difference the user is asking for, because each hour would always spread 0–100. Rejected.
3. **TTC ridership by hour as the night proxy.** The open TTC datasets stopped updating in 2017–2020. Bike Share is current to 2025–2026.

### Risks

| Risk | How it's reduced |
|---|---|
| Night-time foot traffic is **estimated** from Bike Share trips, not counted. Cyclists aren't pedestrians. | Bike Share matches the pedestrian counts closely during the day. The reasons say "estimated from Bike Share trips". |
| At night most blocks fall below the floor of 100 people an hour, so night scores mostly reflect incidents at that hour. | This is intended: it stops near-empty streets from producing extreme ratios. The floor is shown on the rules page. |
| Unknown times recorded as midnight inflate late-night incidents slightly. | The 3-hour window and leaning toward the city pattern dampen this, and it is listed as a limitation. Excluding 00:00 entirely would undercount real midnight incidents. |

## Plan
These steps run on the same branch, each with tests and a commit.

| # | What | Files | Tests | Done when |
|---|---|---|---|---|
| T1 | Activity profile: the script, the CSV with sources and dates, the table and source, loaded by `ingest reference` | `scripts/build_activity_profile.py`, `data/activity_by_hour.csv`, `db/migrations/004_time_of_day.sql`, `ingest/reference.py`, `ingest/registry.py` | 24 rows, factors positive, basis set; header records sources and dates; table loaded with `collected_at` | `ingest reference` loads 24 rows; `/sources` lists `activity_profile` |
| T2 | Scoring by hour: window, shares leaning toward the city pattern, intensity, per person by hour, score across all cells and hours | `scoring/crime.py`, `scoring/build.py` | Criteria 22–24 with hand-worked numbers; wrap-around | `build-scores` stores 24 scores per cell; City Hall at 2 am is above 2 pm (criterion 25) |
| T3 | API `hour` parameter, `time` object, the reason for the hour | `api/locate.py`, `api/routes/cells.py`, `api/routes/risk_scores.py`, `api/routes/route_risks.py`, `api/routes/sources.py` | Criteria 21 and 26: no `hour` means unchanged; 25 returns 422; scores and reasons change with the hour | API tests pass; live check of City Hall at 2 am and 2 pm |
| T4 | Web map time selector; rules page section | `web/index.html`, `web/app.js`, `web/style.css`, `web/rules.html` | Run by hand (criterion 28), with a screenshot | The selector updates the street layer, destination and route |
| T5 | README and implementation record | `README.md`, `04-implementation.md` (addendum) | Full suite | Tests pass; the documents are updated |

## What happens next
Once this is approved, I build T1–T5 and add them to `04-implementation.md` as an addendum. Then phase 5 (test the work) covers everything, including criteria 21–28.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 13:21
- **User's response:** "YES"
- **Revisions before approval:** none
