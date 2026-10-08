# Phase 4 (addition): Do the work: Crime trendlines

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-08  ·  **Status:** Pending approval

## What this step is
Build the approved plan in [01-03-trends.md](01-03-trends.md) (slices T1–T5) with tests, on branch `feature/trends`.

## What was done
Each slice was built in order on `feature/trends`, with tests written first, and committed separately. Real data was checked at each step:
- **Live source:** the Toronto Police Neighbourhood Crime Rates layer, downloaded 2026-10-08.
- **Databases:** Neon `test`, then Neon `main`, as the plan approved.
- **Browser:** the web panel was checked in headless Edge over CDP.

The branch is pushed to GitHub and has **not** been merged to `main`.

## Plan steps
| # | Step | Result | Commit |
|---|---|---|---|
| T1 | Migration 008 and loading the yearly figures | `neighbourhood_crime_years` holds **17,064 rows** (158 neighbourhoods × 9 offences × 2014–2025), each with `collected_at`. The 2025 assault total is 24,686, matching the source. Loaded on Neon `test` and `main`. | `3bcf90e` |
| T2 | Trend calculation stored by `build-scores` | On Neon `main`, **158 of 158** neighbourhoods have `details.trend`. Toronto 2016–2025: violent **+10% (rising)**, property **+5% (flat)**. 2021–2025: violent +17%, property −11%. Recovered Toronto populations: 2,823,026 (2016) and 3,214,722 (2025, equal to the published total). 565 neighbourhood/offence series are "too few to call a trend". Every figure matches the plan. | `f3b9f93` |
| T3 | `trend` on `/risk-scores` and `/neighbourhoods/{id}` | API tests confirm the shape, and that the score and odds are unchanged. | `a9c0f10` |
| T4 | Web Trend section and the rules page | Checked at 1280 px and 390 px, light and dark: no sideways scrolling, chart fits the panel (310 px and 336 px), no console errors. Keyboard: Enter on "5 years" switches the view, the button is marked pressed, focus stays on it, and Yonge-Bay changes to violent +31% and property −26%. A searched point (City Hall) shows its neighbourhood's trend. | `7bf9dbb` |
| T5 | Acceptance check; preview deploy | Three new checks (`trends-2`, `trends-3`, `trends-2b`). **Local: 33 of 33 pass.** The preview built (`uavert-oi6ryi140-sai-project.vercel.app`) but every request fails: Vercel has `DATABASE_URL` and `DB_POOL_MAX` for Production only. **Waiting for you to add them for Preview** (see below). | `ef1d28c` |

Tests: **236 passed** (up from 217), exit code 0.

## Files changed
| File | New / changed | Summary |
|---|---|---|
| `db/migrations/008_crime_years.sql` | New | `neighbourhood_crime_years` table |
| `src/uavert/sources/tps.py` | Changed | `CrimeYear`, `ncr_year_fields`, `parse_crime_years` (stops on any missing figure) |
| `src/uavert/ingest/reference.py` | Changed | `NCR_FIRST_YEAR = 2014`; the neighbourhood load also stores the yearly figures (`store_crime_years`) |
| `src/uavert/scoring/trends.py` | New | Group rates, recovered populations, least-squares change, labels, too-few rule |
| `src/uavert/scoring/build.py` | Changed | `add_trends` puts each neighbourhood's trend and Toronto's into `details.trend` |
| `src/uavert/api/locate.py`, `api/routes/neighbourhoods.py` | Changed | Return `trend` |
| `src/uavert/web/app.js`, `index.html`, `style.css`, `rules.html` | Changed | Trend section (inline SVG chart, toggles, summary, tables, note); "Trends over time" on the rules page |
| `scripts/acceptance_check.py` | Changed | Trend checks |
| `tests/…` | New / changed | `test_trends.py` (15 tests); parsing, build and API tests; fixture `tps/ncr_years_one.json` (real Yonge-Bay record); the API fixture also clears the new table |

## Deviations from the plan
1. **One request, not two.** The yearly fields come in the same request as the neighbourhood boundaries. Listing all 216 field names made the URL too long and the service returned **HTTP 404**, so the request asks for all fields (`*`). The parser still refuses a load with any figure missing.
2. **Toronto's trend is stored with each neighbourhood**, not once. That's about 7 KB per neighbourhood and needs no new table or endpoint.
3. **Groups are always ≥ 10 incidents a year.** On today's data, no neighbourhood's violent or property group falls below 10 a year, so the "too few" label only appears in the by-offence list.
4. **The test fixture had to clear the new table.** The API test fixture deletes neighbourhoods, and the new foreign key blocked that (50 test errors) until the fixture cleared `neighbourhood_crime_years` first. One `test_news` failure came from my real load on Neon `test` (158 real neighbourhoods); it cleared once the fixture could reset the branch again.

## Mistakes and fixes
- **Two wrong test expectations in `test_trends.py`.** One expected 47.4 where the correct rounding gives 47.45. The other used an "odd year" series whose fitted change happens to equal the end-to-end change. I corrected the tests; the code was right.
- **A false keyboard failure in the browser check.** The first keyboard check sent Enter without its character, so the button didn't react. It was a harness error, not a page bug; with a complete key event the toggle works.

## Clean-up
- Reviewed the changed code against the surrounding style.
- The y-axis labels now share one precision ("0 / 20 / 41", not "0.0 / 20 / 41").
- No other changes were needed. The odds table code wasn't refactored to share the new `figuresTable` helper, which is out of scope.

## Known issue until merge
The daily 10:00 UTC refresh runs `build-scores` from `main`'s code, which doesn't write trends. Each daily run until the merge removes `details.trend` from Neon `main` (the yearly table stays). I'll re-run `build-scores` from this branch before each check. Merging fixes it.

## Waiting on you: Vercel Preview settings
In the Vercel project settings, add `DATABASE_URL` (the Neon `main` direct host, as Production uses) and `DB_POOL_MAX=2` to the **Preview** environment. My permission settings blocked me from writing secrets into Vercel. Then I'll redeploy the preview, run the acceptance check on it, and record the results in the test report.

## Follow-up ideas
- "This year so far" (2026 to date compared with the same months of 2025) from incident data.
- A Statistics Canada Crime Severity Index trend for Peel and the other GTA regions.
- Note: [05-test-report.calibration-crowds-heat.md](05-test-report.calibration-crowds-heat.md) recorded that pushing to `main` did *not* auto-deploy production. Check how production deploys before the merge.

## What happens next
Once you've added the Preview settings and approved this document, I'll write `05-test-report.trends.md` (preview acceptance check, review of the diff) for approval. Then I'll ask before merging to `main`.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
