# Phases 1–3 (addition): Crime trendlines

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-08  ·  **Status:** Approved

## What this step is
Define, design and plan one addition: show how reported crime in a neighbourhood has changed over the last 10 years (and the last 5), as a chart with a fitted trendline and a plain-language label such as "rising" or "falling", next to the same trend for Toronto. One approval covers all three phases.

## What was done
- Read the current crime pipeline: incidents are loaded only from 2025-01-01 (`ingest/crime.py`, `START_DATE`), homicides from 2023, and the neighbourhood table is loaded for 2025 only (`ingest/reference.py`, `NCR_YEAR = 2025`). So the database holds no history yet.
- Checked what Toronto Police publishes (2026-10-08):
  - **Neighbourhood Crime Rates** (the layer we already use, `tps_ncr`): 158 neighbourhoods, each with a yearly count **and** a yearly rate per 100,000 residents for **2014 to 2025** for 9 offence types (assault, auto theft, bike theft, break and enter, homicide, robbery, shooting, theft from vehicle, theft over $5,000). There are no missing values: 0 empty counts and 0 empty rates across 17,064 neighbourhood/offence/year cells. Same licence as today (Open Government Licence – Ontario, commercial use allowed with attribution).
  - **Major Crime Indicators** incidents: 497,606 records, the latest dated 2026-09-30, so the current year is available as incidents. It isn't needed for full-year trends (see Out of scope).
- Worked the numbers for Toronto and three neighbourhoods to see what the trends look like (below).
- Reviewed the odds addition (`01-03-odds.md`) so the trend panel follows the same pattern: it's calculated in `build-scores`, stored in `neighbourhood_scores.details`, and returned by the API with nothing calculated per request.

## 1. Definition

### The problem
The score and the odds describe the latest year only. They can't say whether a place is getting better or worse, which is one of the first questions people ask. Sai wants trendlines built from 5–10 years of data.

### What the user sees
For any searched address, and on the neighbourhood panel, a new **Trend** section under the odds:

> **Reported crime in Yonge-Bay Corridor, per 1,000 residents** · [10 years] [5 years]
>
> *(chart: one point per year, a solid line for the neighbourhood, a dashed fitted trendline, and a faint line for Toronto)*
>
> - **Violent crime:** falling, about 38% lower over 2016–2025 (Toronto: rising, +10%)
> - **Property crime:** falling, about 35% lower over 2016–2025 (Toronto: roughly flat, +5%)
>
> *Per resident, so places with many visitors look higher. Shows reported incidents only. 2020–2021 were pandemic years with less activity. Source: Toronto Police Service, Neighbourhood Crime Rates, 2014–2025.*
>
> ▸ By offence (9 rows: offence, 2025 count, trend over the chosen period, or "too few to call a trend")

Switching to **5 years** redraws the chart and labels for 2021–2025. For Yonge-Bay that reads "violent crime: rising, +31%", which is why both views are offered: the 5-year view starts from the 2021 pandemic low.

The rules page gets a short section explaining the method.

### Figures from the published data (2026-10-08)
Rates per 1,000 residents. "Change" is the fitted trendline's change from the first to the last year of the window.

| Place | Group | 2016 | 2021 | 2025 | 10-year change (2016–25) | 5-year change (2021–25) |
|---|---|---|---|---|---|---|
| Toronto | Violent | 8.1 | 7.4 | 8.6 | +10% (rising) | +17% (rising) |
| Toronto | Property | 7.9 | 8.4 | 7.5 | +5% (flat) | −11% (falling) |
| Yonge-Bay Corridor | Violent | 47.4 | 27.1 | 36.9 | −38% (falling) | +31% (rising) |
| Moss Park | Property | 19.3 | 18.2 | 9.7 | −52% (falling) | −43% (falling) |
| West Humber-Clairville | Property | 21.4 | 29.3 | 24.7 | +38% (rising) | −20% (falling) |

### Acceptance criteria
1. The database holds the published yearly counts and rates for all 158 neighbourhoods, 9 offences and 12 years (2014–2025): 17,064 rows, each with `collected_at`.
2. `/api/v1/risk-scores` and `/api/v1/neighbourhoods/{id}` return a `trend` object with:
   - the yearly series (violent, property, all, and each of the 9 offences) for the neighbourhood and for Toronto;
   - for each group and each window (10 and 5 years), the fitted change in percent, the direction label, and the counts behind it.
3. Toronto's 10-year figures match the table above: violent +10%, property +5%, within 1 percentage point.
4. The direction label is **rising** for a change of +10% or more, **falling** for −10% or less, and **roughly flat** in between. A series averaging fewer than 10 incidents a year over the window shows "too few to call a trend" instead of a label. On today's data that applies to 565 of the 1,422 neighbourhood/offence series, mostly homicides and shootings in single neighbourhoods; the violent and property groups are much larger.
5. The chart and toggle work on the search result and the neighbourhood panel, at laptop and phone widths, in light and dark themes, and from the keyboard. The chart has a text alternative (the yearly figures).
6. Wording: it never says "safe" or "safer"; it says "reported" and names the years and the source.
7. The risk score, bands, odds and every existing reason are unchanged: existing tests pass, and the acceptance check still passes with new trend checks added.

### Out of scope (follow-ups)
- **This year so far** (2026 to date compared with the same months of 2025). Possible from the incident data we already load, but it covers only 7 of the 9 offences, and part-year comparisons need care. Worth a separate small addition.
- Street-block trends: block counts are too small to support a trend.
- Peel, York and other regions: blocked on permissions (see [gta-expansion-notes.md](gta-expansion-notes.md)). Statistics Canada's Crime Severity Index could later give a region-level trend.
- Forecasting future years.

## 2. Design

### Data
- **New table `neighbourhood_crime_years`** (migration `008_crime_years.sql`) with columns `neighbourhood_id, year, offence, count, rate_per_100k, source_key ('tps_ncr'), collected_at`; unique on (neighbourhood, year, offence).
- It's loaded in the existing `tps_ncr` step of the reference ingest, with one extra request to the same layer: all year fields, no geometry. The loader checks it receives 158 neighbourhoods and every year from 2014 to `NCR_YEAR`.
- Raw published figures are stored as published, so the trend can always be recalculated and traced back to the source.

### Groups
| Group | Offences in the yearly table |
|---|---|
| **Violent** | assault, robbery, homicide, shooting |
| **Property** | break and enter, auto theft, theft over $5,000, theft from vehicle, bike theft |
| **All** | all 9 |

These are not the same as the odds panel's high, medium and low levels. The yearly table counts all assaults together, so common assault can't be separated from assault with a weapon. The panel uses its own two group names so the two panels aren't confused.

### Calculation (`scoring/trends.py`, new)
- **Neighbourhood group rate per year:** the sum of the published per-100,000 rates of the offences in the group. All offences in a year share the same population, so this equals group count ÷ population. It's shown per 1,000 residents (÷ 100) because those numbers are easier to read.
- **Toronto rate per year:** the summed counts ÷ the summed neighbourhood populations. Each neighbourhood's population for a year is recovered as count ÷ rate × 100,000, using the median across offences with a non-zero count. This gives 2,823,026 for 2016 and 3,214,722 for 2025; the 2025 figure equals the published `POPULATION_2025` total.
- **Trendline:** an ordinary least-squares straight line through the yearly rates in the window. The change is (fitted last year − fitted first year) ÷ fitted first year. A fitted line is less affected by one unusual year than comparing two single years.
- **Windows:** 10 years = 2016–2025, 5 years = 2021–2025. Both are calculated in `build-scores` and stored in `neighbourhood_scores.details.trend`, with Toronto's stored once.

### Assumptions (please correct any that are wrong)
1. A neighbourhood-level trend is acceptable on a street-level search result, labelled with the neighbourhood's name, the same as the odds.
2. Per resident is the right measure (not raw counts). Yonge-Bay Corridor's population grew from about 10,300 in 2014 to 16,661 in 2025, so raw counts would overstate its rise.
3. ±10% is the threshold for "roughly flat", and 10 incidents a year is the minimum for a label.
4. 10 years is the default view. 2014 and 2015 are stored but not charted, because you asked for 5–10 years.

### Alternatives considered
- **Comparing two single years** ("up 18% since 2016"): rejected. It's too sensitive to one odd year; for example, 2020 was a pandemic year.
- **Comparing 3-year averages:** reasonable, but the number wouldn't match the line drawn on the chart. The fitted trendline is both the number and the line.
- **Rebuilding history from incidents** (497,606 records): unnecessary for full years, because Toronto Police already publishes the yearly counts and rates per neighbourhood. That route would also miss theft from vehicle and bike theft.
- **A charting library:** not needed. A small inline SVG chart keeps the page light, and it's what the rest of the page does: only Leaflet is loaded from a CDN.

## 3. Plan

Branch: `feature/trends` from `main`. `main` now deploys production, so this work stays off `main` until the test report is approved.

| # | Slice | Files | Test first |
|---|---|---|---|
| T1 | Migration `008_crime_years.sql`; parse all yearly fields; load 17,064 rows in the `tps_ncr` step | `db/migrations/008_crime_years.sql`, `sources/tps.py`, `ingest/reference.py` | parsing a recorded feature gives 9 × 12 rows with counts and rates; the loader rejects a missing year or a neighbourhood count other than 158 |
| T2 | Trend calculation: group rates, Toronto population and rate, least-squares change, labels, too-few rule; stored by `build-scores` | `scoring/trends.py` (new), `scoring/build.py` | fit on known series (flat → 0%, a straight line → its exact change); thresholds at +10% and −10%; too few below 10 a year; Toronto 2016 and 2025 populations from a fixture |
| T3 | API: `trend` on `/risk-scores` and `/neighbourhoods/{id}` | `api/locate.py`, `api/routes/neighbourhoods.py` | API tests for the shape, and that the score and odds are unchanged |
| T4 | Web: Trend section (inline SVG chart, trendline, Toronto line, 10y/5y toggle, offence list, text alternative); rules page section | `web/app.js`, `web/index.html`, `web/style.css`, `web/rules.html` | checked in a headless browser at laptop and phone widths, light and dark, with the keyboard |
| T5 | Apply the migration and load the data on Neon `test`, then `main`; rebuild scores; add trend checks to the acceptance check; Vercel preview deploy from the branch | `scripts/acceptance_check.py` | acceptance check passes locally and on the preview |

**Actions outside the machine** (approving this plan approves them): applying migration 008 to Neon `test` and `main` (it adds one table and changes nothing that exists, so the code now on `main` keeps working); running the reference ingest and `build-scores` on Neon `main` (it rewrites the score tables, as every rebuild does); pushing `feature/trends` to GitHub; and a Vercel **preview** deploy. **Merging to `main` (production) is not included.** I'll ask for it separately after the test report.

**Rough size:** about a day.

## What happens next
Once this is approved, I'll build T1–T5 with tests first, then write `04-implementation.trends.md` and `05-test-report.trends.md` for approval, and add rows to the end-to-end checklist in `06-e2e-signoff.md` for you to test.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-08 11:30
- **User's response:** "yes"
- **Revisions before approval:** none
