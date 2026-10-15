# 5. Verify the work: rate limits, edge caching and a read-only database user

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Approved
**Verifies:** [01-03-security.md](01-03-security.md), criteria 43–47, built in [04-implementation.security.md](04-implementation.security.md).

## What this step is
This is the evidence for each criterion that can be checked before production. The rest needs production and goes to T4 and your test list.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | "311 passed in 86.64s" (exit code 0) |
| Acceptance check, local app as `uavert_web` on the real data | `python scripts/acceptance_check.py http://127.0.0.1:8013` | "45 of 45 checks passed" |

**Compared with the baseline:** 286 tests passed on `main` after the news merge. There are now 311 (25 new), all passing.

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 43 | Successful API `GET`s carry the edge-cache header; errors, `/health` and pages don't | `tests/api/test_caching.py`, 8 tests. Acceptance check `sec-43`: "Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=300". | Passed |
| 44 | Second request is an edge-cache `HIT` in production | Needs Vercel's CDN; checked in T4. `sec-44` is in the acceptance check for that run. | Waiting for production |
| 45 | Firewall rule live; a burst of 130 gets 429 after about 120; normal use doesn't | Configured in T4 | Waiting for production |
| 46 | `uavert_web` on the test branch reads everything, saves lookups, is refused changes | `tests/test_web_role.py`, 17 tests. It is `uavert_web`, with no superuser, create-role or create-database rights, and not in `neon_superuser`. It reads 8 tables, writes `geocode_cache` and `route_cache`, and gets `InsufficientPrivilegeError` for insert into `incidents`, delete from `neighbourhoods`, update `neighbourhood_scores`, delete from `geocode_cache`, truncate `news_events`, create a table and drop a table. | Passed |
| 47 | The website works as `uavert_web` | **Locally on the real data:** 43 of 43, then 45 of 45 with the new checks. A new address lookup ("1 Dundas St W") answered 200 and saved its row. Neon listed the local app's connection as `uavert_web`. **Production:** after your Vercel switch (T4). | Passed locally; production in T4 |

## Code review findings

| # | Finding | Action |
|---|---|---|
| 1 | Migration 011 reached production early (deviation 1 in the build record) | No effect, checked: the role didn't exist, so nothing was granted. Recorded. |
| 2 | **Security:** the role's password must not leak | It was generated locally and never printed. It's stored only in the git-ignored `.env` (test branch) and in a file outside the repository (production). |
| 3 | **Security:** the role must not inherit Neon's admin rights | It's created with SQL, and the script stops if it finds `neon_superuser` membership. A test checks it. |
| 4 | **Correctness:** caching must not repeat errors to other visitors | Only status 200 is cached. Tested with 422 and 404. |
| 5 | **Correctness:** cached live data is older | Up to about 10 minutes, documented in the README. Collection is hourly anyway. |
| 6 | **Compatibility:** response bodies don't change, and the local app behaves the same | Only a header is added. The existing test suite is unchanged and passes. |

## Could not verify
These are checked in T4 and your test list:
- **Criteria 44 and 45:** they need Vercel's CDN and Firewall.
- **Criterion 47 in production:** it needs your switch of `DATABASE_URL` in Vercel.
- **Normal use under the rate limit from a real phone** (row 52).

## What happens next
Once you approve this and the build record, I run T4 as described in the build record. Your one step is the Vercel `DATABASE_URL` switch.

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-15 15:24
- **User's response:** "approve"
- **Revisions before approval:** none
