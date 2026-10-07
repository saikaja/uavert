# 4. Do the work (solidify + Vercel): Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Approved

## What this step is
This document records building the additions agreed in [01-03-solidify.md](01-03-solidify.md) (approved 2026-10-01 14:05): the GitHub backup, saved lookups, automatic refresh, the fairness check, homicide smoothing and Vercel hosting. Test results are in [05-test-report.solidify.md](05-test-report.solidify.md).

## What was done
Steps S1–S6 were built in order on `feature/backend-foundation`, each with tests, then committed and pushed to GitHub. The full suite passes: **164 tests** (`python -m pytest`, exit code 0).

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| S1 | Private GitHub repository `saikaja/uavert`, both branches pushed | Done: private; secret search of the remote copy clean | (push only) |
| S2 | Saved lookups: `geocode_cache` (30 days), `route_cache` (7 days); also used by the news geocoding | Done | `024a651` |
| S3 | Homicides: 2023–2025 average for neighbourhoods; ⅓ for 3 years on streets; homicides loaded from 2023 (219 records) | Done | `8d5ff6c` |
| S4 | Fairness check: census income CSV and script, `neighbourhood_census`, `fairness_checks` per build, `/scoring-rules` and the rules page | Done | `4f1f819` |
| S5 | Background refresh while serving (every 30 min by default); GitHub Actions hourly and daily refresh with the `DATABASE_URL` secret and `DATA_BRANCH` variable | Done | `a799794` |
| S6 | Vercel: `index.py`, `vercel.json` (`cle1`), pool opened on first request, `X-Robots-Tag` and `robots.txt`, production environment variables, production deploy, Git connection | Done: https://uavert.vercel.app | `5274450`, `f0728c8`, `8bd4f78` |
| S7 | Tests again, README, these records, and the phase 6 checklist | Done (this document, the test report, and an updated `06-e2e-signoff.md`) | this commit |

## Results on the real data
- **Homicide smoothing:**
  - Bayview Woods-Steeles moves from rank 63 to 112, and Mount Dennis from 41 to 86 (they were 137 and 98 under the old demo weights)
  - Yonge-Bay Corridor stays #1
  - 67 of 158 neighbourhoods now differ in band from the demo, down from 75
  - [csi-vs-demo-ranking.md](csi-vs-demo-ranking.md) is regenerated, with a section on this change
- **Fairness check** (all 158 neighbourhoods): scores against median household income, ρ = **−0.28**; against the low-income share, ρ = **+0.24** → "Scores don't mostly follow income" (review threshold 0.5).
- **Saved lookups:** after a server restart, all 5 demo addresses and 2 demo routes were answered from the database. Their `collected_at` was unchanged, so no outside service was called, and answers took about 0.35 s instead of about 1 s.
- **GitHub Actions:** the first manual run (`36905963448`, full reload) passed in 1 min 17 s: migrations, live sources (GDELT refused and was recorded as a warning), crime, traffic and scores.
- **Vercel:** built with Python 3.12 from `pyproject.toml`; production at https://uavert.vercel.app.

## Files changed

| File | New / changed | Summary |
|---|---|---|
| `db/migrations/005_lookup_cache.sql`, `006_fairness.sql` | New | Saved lookups; census income and fairness history |
| `src/uavert/sources/geocode.py`, `routing.py` | Changed | Memory, then the database, then the outside service; answers saved with `collected_at` |
| `src/uavert/ingest/steps.py` | New | Ingest steps shared by the command line and the background refresh |
| `src/uavert/ingest/cli.py`, `crime.py`, `reference.py`, `registry.py`, `news.py` | Changed | Refresh option on `serve`; homicides from 2023; census load; new source; saved geocoding for news |
| `src/uavert/scoring/build.py`, `crime.py`, `fairness.py` (new) | Changed / new | Homicide averaging; fairness check stored per build |
| `src/uavert/api/app.py`, `routes/sources.py`, `locate.py`, `config.py`, `db.py` | Changed | Background refresh; pool opened on first request; noindex and `robots.txt`; fairness in `/scoring-rules`; pool size setting |
| `src/uavert/web/rules.html` | Changed | "Fairness check" section |
| `index.py`, `vercel.json`, `.vercelignore`, `.gitattributes`, `.gitignore` | New / changed | Vercel; consistent line endings; no tokens or `.env` uploaded |
| `.github/workflows/refresh.yml` | New (also on `main`) | Hourly and daily refresh |
| `data/neighbourhood_income_2021.csv`, `scripts/build_neighbourhood_income.py` | New | Census income with source and retrieval date |
| `scripts/acceptance_check.py`, `scripts/compare_rankings.py`, `README.md` | Changed | Check compares against the source registry; report notes the homicide averaging; README covers hosting and refresh |
| tests (`test_saved_lookups.py`, `test_fairness.py`, `test_refresh.py`, plus additions to `test_build.py` and `api/test_read_endpoints.py`) | New / changed | Criteria 30–39 |

## Deviations from the plan
1. **The workflow file is on `main` as well.** GitHub only runs schedules for workflows on the default branch, so `.github/workflows/refresh.yml` alone was committed to `main` (`148a3c5`). The app code is not on `main`. The repository variable `DATA_BRANCH = feature/backend-foundation` makes the scheduled runs use the tested branch until the merge; delete it after merging.
2. **Vercel team.** `vercel link` created the project under your Vercel team **`sai-project`**, and connected it to the GitHub repository at the same time. `main` is production, so **nothing should be pushed to `main` until the app is merged**, or Vercel would deploy `main`'s current content (documents only) to production.
3. **`.gitignore`.** `vercel link` added `.env*` to `.gitignore`. An exception was added so the `.env.example` template stays tracked.
4. **Windows line endings (my mistake).** My edit scripts had been saving some files with Windows line endings (49 files), which made some diffs noisy (for example `db.py`). Fixed with `.gitattributes` (`eol=lf`) and a one-time conversion (`ee7e97a`). No behaviour changed; the suite passed before and after.
5. **Test file append that didn't land (my mistake).** Two new tests (noindex, pool on first request) were missing from my first commit because a shell quoting problem swallowed the append. They were added in `f0728c8`.
6. **Fairness numbers.** The preview in the plan (−0.23 / +0.18) was before homicide smoothing. The stored check after it is −0.28 / +0.24, still well under 0.5.

## Clean-up
No separate simplifier pass was run for this round. New code reuses existing helpers: `run_steps` is now shared by the command line and the refresh, and saved lookups sit inside the existing `Geocoder` and `Router`. `pyflakes` reports no issues.

## Follow-up ideas
- **After you sign off:** merge into `main`, then delete the `DATA_BRANCH` variable. After that, pushes to `main` deploy to production.
- **Actions versions:** move the workflow to newer action versions; GitHub warns that Node.js 20 actions are deprecated.
- **Smaller items:**
  - a scatter chart of score against income on the rules page
  - a custom domain
  - a licensed news source before sharing the public link widely

## What happens next
Once this and the test report are approved, the phase 6 checklist ([06-e2e-signoff.md](06-e2e-signoff.md), updated with the hosted link and the new checks) is yours to run.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-01 18:07
- **User's response:** "approve number 2"
- **Revisions before approval:** none
