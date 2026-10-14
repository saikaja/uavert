# Phase 5 (addition): Verify the work: Crime trendlines

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-08  ·  **Status:** Approved

## What this step is
Prove every acceptance criterion in [01-03-trends.md](01-03-trends.md) with real evidence before the hand-off, review the diff, and fix what the review finds.

## What was done
- Ran the full test suite on branch `feature/trends`.
- Ran the scripted acceptance check against a local server reading Neon `main`.
- Checked the web panel in headless Edge.
- Reviewed the diff (`main..feature/trends`) on five axes: correctness, readability, architecture, security, performance. The review found one real problem, which is now fixed with tests.
- Tried a fresh clone and clean install.
- The **hosted preview could not be checked yet** (see "Could not verify").

## Automated checks
| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | "238 passed in 58.06s", exit 0 |
| Acceptance check, local server on Neon `main` | `python scripts/acceptance_check.py http://localhost:8077` | "33 of 33 checks passed", exit 0 |
| Clean install on Vercel (Python 3.12, from `pyproject.toml`) | `vercel deploy` | "Build Completed", deployment `READY` |

Compared with the baseline before this addition: 217 tests passed and 30 acceptance checks passed. Nothing that passed before fails now; 21 tests and 3 acceptance checks were added.

## Acceptance criteria
| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | 17,064 yearly rows with `collected_at` | Query on Neon `main`: `count = 17064`, 158 neighbourhoods, years 2014–2025; `test_schema` includes the table among those that must have `collected_at` | Pass |
| 2 | `trend` on both endpoints with series and windows | `test_neighbourhood_detail_has_trend`, `test_address_carries_its_neighbourhoods_trend`; acceptance `trends-2`, `trends-2b` (live) | Pass |
| 3 | Toronto 10-year: violent +10%, property +5% (±1) | Acceptance `trends-3`: "Toronto 2016-2025: violent 10%, property 5%" | Pass |
| 4 | Labels: ±10% thresholds; under 10 a year is too few | `test_direction_thresholds` (7 cases, at and either side of each threshold); 565 too-few series on real data, as the plan said | Pass |
| 5 | Chart and toggles: laptop and phone, light and dark, keyboard, text alternative | Headless Edge at 1280 and 390 px, light and dark: chart 310 and 336 px wide inside the panel, no sideways scroll, no console errors; keyboard Enter on "5 years" switches the view and keeps focus; the chart's `aria-label` gives the trend in words; a "Yearly figures" table carries the numbers | Pass (local). You'll check it on the hosted site in E2E |
| 6 | Wording: never "safe" or "safer"; says reported, names years and source | Acceptance check 9: "no band or label containing 'safe' in 5 live responses"; panel text reviewed: "Reported incidents only… Source: Toronto Police Service, Neighbourhood Crime Rates", years in every summary | Pass |
| 7 | Score, bands, odds and reasons unchanged | All earlier tests pass; API tests assert score 80 and odds intact; acceptance `odds-1`, `odds-3` and `12` give the same values as before (Yonge-Bay 64; Toronto any 1 in 73) | Pass |

## Real-app checks
- **Local server on Neon `main`:**
  - City Hall: street 64 (elevated); neighbourhood Yonge-Bay Corridor, violent −38% over 10 years.
  - `/neighbourhoods/31`: has a trend.
  - Rules page: has the "Trends over time" section, and the "How this is worked out" link points to it.
- **Neon `main` after `build-scores`:** 158 of 158 neighbourhoods have `details.trend`.

## Code review findings
| # | Finding | Action |
|---|---|---|
| 1 | **Required, correctness.** If the yearly table were incomplete (a neighbourhood missing a figure, or `NEIGHBOURHOOD_YEAR` moved to 2026 before Toronto Police publishes 2026), `trends.trends` raised `KeyError`. That would stop the **whole** `build-scores` run, so no scores would update at all. | **Fixed** (`Fix: an incomplete yearly table…`). A neighbourhood with a gap gets no trend and isn't counted in Toronto's figures. If the scoring year isn't loaded, scores still build without trends and a warning is printed. Regression tests: `test_a_neighbourhood_missing_a_figure_is_left_out_not_a_crash`, `test_trends_wait_for_the_scoring_year_to_be_published`. |
| 2 | Nit. `/neighbourhoods/{id}` returns the trend twice, once under `crime_details` and once as `trend`, the same as `odds` already does. About 7 KB extra. | Left as is, matching the existing pattern. Noted as a follow-up. |
| 3 | Security | Queries are parameterised. Page text is set with `textContent` or `setAttribute`, never as HTML. No new dependencies. No secrets in code. | 
| 4 | Performance | `build-scores` reads 17,064 rows once (the whole build took 10.6 s). The API reads the stored JSON, with nothing calculated per request. Responses grow by about 7 KB. |

## Could not verify
1. **The hosted preview.** The preview builds, but every request fails with `database_url Field required`, because Vercel's `DATABASE_URL` and `DB_POOL_MAX` are set for Production only. My permission settings block me from writing secrets into Vercel. **Waiting for you to add them for Preview**; then I'll redeploy and run `acceptance_check.py` against it, and update this report.
2. **A fresh local install.** In a fresh clone, Windows Smart App Control blocked the newly installed `pydantic_core` DLL ("An Application Control policy has blocked this file"). The Vercel build covers this instead: a clean install from `pyproject.toml` on Python 3.12, which succeeded.
3. **Trends staying in place on `main`.** Until the merge, the daily 10:00 UTC refresh rebuilds scores with `main`'s code and removes the trends. They come back on the next `build-scores` from this branch, and permanently once merged.

## What happens next
Once you've added the Preview settings, I'll run the acceptance check on the preview and record the result here. After you approve this report, I'll add end-to-end rows for the trend panel to [06-e2e-signoff.md](06-e2e-signoff.md) and ask before merging `feature/trends` to `main`.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-08 11:58
- **User's response:** "yes can u send the change to vercel so i can test as well"
- **Revisions before approval:** none
