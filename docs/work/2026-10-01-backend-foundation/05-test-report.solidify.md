# 5. Test the work (solidify + Vercel): Uavert backend foundation and Toronto web demo

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval

## What this step is
This step checks the additions in [01-03-solidify.md](01-03-solidify.md) (criteria 29–39) with real evidence, and re-checks the earlier criteria on both the local server and the hosted site. The build record is [04-implementation.solidify.md](04-implementation.solidify.md).

## What was done
- Ran the full test suite and lint after each step.
- Ran the live acceptance check (`scripts/acceptance_check.py`) against both the local server and https://uavert.vercel.app.
- Checked GitHub, GitHub Actions and Vercel directly.

All results are from 2026-10-01, about 14:05–14:35 Toronto time.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | `164 passed in 41.89s`, exit code 0 |
| Lint | `python -m pyflakes src tests scripts index.py` | no output (no issues) |
| Live acceptance check, hosted | `python scripts/acceptance_check.py https://uavert.vercel.app` | `22 of 22 checks passed` |
| Live acceptance check, local | `python scripts/acceptance_check.py` | `22 of 22 checks passed` |

**Compared with the last report:** 148 → 164 tests. Every earlier test still passes.

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 29 | Private repository with both branches; no secrets | `gh repo view`: `{"isPrivate":true,"visibility":"PRIVATE"}`. `git ls-remote`: `main` and `feature/backend-foundation`. A fresh clone of the remote searched across all history: ".env files: 0", "npg_ passwords: 0", "connection strings with passwords: 0". `.env.local` (Vercel token) and `.vercel/` are not tracked | Pass |
| 30 | Saved address and route reused after a restart without calling the outside service | `test_address_is_reused_after_restart_without_calling_nominatim` and `test_route_is_reused_after_restart_and_expires_after_7_days`: the fake Nominatim and OSRM were each called once across two instances. Live: after a server restart, the 5 demo addresses and 2 routes were answered with `collected_at` unchanged ("newest collected 2026-10-01 18:08:22"), in about 0.35 s | Pass |
| 31 | Expiry after 30 days (addresses) and 7 days (routes); `collected_at` on every row | `test_saved_address_expires_after_30_days`, the route expiry part of the test above, `test_not_found_is_saved_too` | Pass |
| 32 | The local refresh runs on a timer, records failures and keeps going | `test_one_refresh_cycle_with_a_failing_source` ("alerts" failed, the later sources still ran), `test_refresh_never_raises_even_if_the_database_is_unreachable`, `test_refresh_is_off_unless_asked_for`. Live: on server start, `ingest_runs` gained `eccc_aqhi ok 14:17:48`, `eccc_alerts ok`, `news_cbc ok`, `news_gdelt running` | Pass |
| 33 | GitHub Actions: hourly live refresh, daily full reload, using a secret; first manual run succeeds | Run `36905963448` (manual, full): "✓ refresh in 1m17s". Every step passed; the log shows "aqhi: ok … news_cbc: ok … news_gdelt: FAILED … ##[warning]Some live sources failed; earlier data was kept … crime: ok … traffic: ok … Scored 158 neighbourhoods and 5748 street cells". The matching rows appear in `ingest_runs`. The secret `DATABASE_URL` and variable `DATA_BRANCH` are set | Pass |
| 34 | Fairness check stored with `computed_at`, shown in `/scoring-rules` and on the rules page | Database: `rho_income -0.283, rho_low -0.236… n 158, label "Scores don't mostly follow income", census_year 2021, computed_at 2026-10-01 18:13:42Z`. Test: `test_scoring_rules_include_latest_fairness_check`. The rules page script parses (Node) | Pass |
| 35 | "Review the weights" label when \|ρ\| ≥ 0.5 | `test_label_uses_the_build_plan_threshold` (4 cases); `test_spearman_known_values` (hand-worked 0.8) | Pass |
| 36 | One 2025 homicide counts a third; the two biggest movers checked | `test_neighbourhood_homicides_use_a_three_year_average`. Live: Bayview Woods-Steeles rank 63 → 112, Mount Dennis 41 → 86 | Pass |
| 37 | Homicides from 2023 loaded; streets count each at ⅓ for 3 years | `ingest crime`: "tps_homicides: 219 records fetched, 209 stored". Test: `test_street_homicides_count_a_third_for_three_years` (2 years ago counts 7,042/3; 4 years ago counts 0) | Pass |
| 38 | The Vercel link serves the map; health 200; destination and route work | Hosted acceptance check: 22 of 22, including "health 200 in 0.24s", "100 Queen St W … street 88 high … 0.17s", "Union Station -> Kensington: 2840 m, score 96 high, 1 stand-out stretch(es), 0.12s", "/ -> 200". Screenshot `screenshots/05-vercel-production.png` | Pass |
| 39 | `X-Robots-Tag: noindex`, `robots.txt`, database URL only in Vercel | `curl` against the hosted site: `/api/v1/health`, `/`, `/robots.txt` and `/api/v1/sources` all return "x-robots: noindex, nofollow"; `/robots.txt` → "User-agent: * Disallow: /". `vercel env ls production`: `DATABASE_URL Hidden Secret Production`. Test: `test_search_engines_are_told_not_to_index` | Pass |

**Earlier criteria on the hosted site:** the same 22 live checks pass on https://uavert.vercel.app as on the local server (criteria 2–4, 9–15, 19, 21, 25–27). The hosted site answers faster because saved lookups skip the outside services.

## Real-app checks
- **Hosted site:** home page, rules page, API docs, health, sources, destination, route, error cases and the hour option, all over the public internet (22 checks).
- **GitHub Actions:** one full scheduled-style run, by hand.
- **Local server:** restarted twice to prove saved lookups, and once more to watch the background refresh run.

## Code review findings
No separate code-review pass was run for this round. Lint is clean and every new behaviour has tests. Issues found while building:
- the Windows line endings and the swallowed test append
- the acceptance check's hard-coded source count, which wrongly failed criterion 4 once the census source was added. The script now compares against the source registry.

All are fixed and recorded in the build record.

## Could not verify
These go into the phase 6 checklist:
1. **The scheduled runs** (hourly at :17, daily at 10:00 UTC) haven't fired yet. Only the manual run was observed. Check the Actions tab after a few hours.
2. **Using the hosted site in a browser:** clicks, zooming, the time selector, and phone layout. Same as before: pages load and render, but the interactions weren't automated.
3. **Vercel's region:** the build ran in `iad1`, and `vercel.json` asks for `cle1` for the function. That wasn't confirmed in the Vercel dashboard. Speed was fine either way (0.1–0.4 s per request).
4. **Local server at the time of writing:** it was stopped by my background-task time limit, and restarting it was blocked by a transient tool error. Start it yourself with the commands in `06-e2e-signoff.md`; the hosted site doesn't depend on it.

## What happens next
Once this and the build record are approved, you run the updated phase 6 checklist ([06-e2e-signoff.md](06-e2e-signoff.md)).

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
