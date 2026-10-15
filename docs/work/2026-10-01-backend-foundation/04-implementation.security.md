# 4. Do the work: rate limits, edge caching and a read-only database user

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Builds:** [01-03-security.md](01-03-security.md) (approved 2026-10-15, "approve").

## What this step is
This records how the approved plan was built, with the evidence.

## What was done
- **Branch:** `feature/security`, from `main` at `c9cc1ed`. Steps T1–T3, each with tests and a commit. T4 (production) waits for your approval.
- **Approach:** tests first for the caching headers (5 failed before the change) and for the read-only user.
- **The read-only user, `uavert_web`, now exists in two places:**
  - **on the Neon `test` branch:** its connection string is in the local `.env` as `TEST_WEB_DATABASE_URL`; `.env` is not in git
  - **on Neon `main`, as planned in T2:** its connection string is in `C:\Users\saika\uavert-web-database-url.txt`, outside the repository

  The password was never printed. Nothing uses the user in production yet.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | Caching headers: `Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=300` on successful API `GET`s other than `/health`; none on errors or pages | 8 tests (5 endpoints cached; 422, 404, `/health` and `/` not) | `e1d0c23` |
| T2 | `scripts/create_web_role.py` (creates the role with SQL, applies the grants, checks it isn't in `neon_superuser`, connects as it, writes the URL without printing it); migration 011 (grants); `tests/test_web_role.py` | 17 tests on the test branch: reads 8 tables, saves to both lookup tables, and is refused 7 kinds of change ("permission denied"). On `main`: "Created uavert_web; connected as uavert_web; grants applied". The local app as `uavert_web` on the real data: **43 of 43**; a new address lookup saved its answer (`geocode_cache` row at 19:20 UTC). | `4c0c3d6` |
| T3 | README (hosting, protection, limits), acceptance checks `sec-43` and `sec-44`, E2E row 52 | Full suite 311 passed. Acceptance check locally as `uavert_web`: **45 of 45**. | `186d916` |
| T4 | Production: merge and deploy; Firewall rule; your Vercel switch; production checks | **Not done.** Waits for your approval. | — |

## Files changed

| File | New / changed | Summary |
|---|---|---|
| `src/uavert/api/app.py` | Changed | `EDGE_CACHE` header in the existing middleware |
| `src/uavert/config.py` | Changed | `test_web_database_url` setting (tests only) |
| `db/migrations/011_web_role.sql` | New | Grants to `uavert_web` where it exists: read all tables, write the two lookup tables, read future tables |
| `scripts/create_web_role.py` | New | Create the role, or give it a new password |
| `tests/api/test_caching.py`, `tests/test_web_role.py` | New | Criteria 43 and 46 |
| `scripts/acceptance_check.py`, `README.md`, `06-e2e-signoff.md` | Changed | As listed in T3 |

## Deviations from the plan
1. **Migration 011 was applied to Neon `main` early, by mistake.**
   - I ran `uavert migrate` to prepare the test branch, but the first command in that line used the default connection, which is production.
   - The migration only grants rights if `uavert_web` exists, and it didn't exist on `main` at that moment (checked straight afterwards), so it changed nothing. It's recorded as applied there.
   - The grants on `main` were then made by `create_web_role.py`, which runs the same SQL, when it created the user as planned.
   - **Impact:** none on the site. T4 no longer needs to run the migration.

## Clean-up
I reviewed the diff (8 files).
- **Caching** reuses the existing middleware, with one constant.
- **`create_web_role.py`:** the only SQL built from text is the role command, with a password from `secrets.token_urlsafe` (letters, digits, `-` and `_` only). Everything else uses parameters.
- **No changes to scoring or to the web page.**

## Follow-up ideas
- **Cache hits for street cells:** each map view asks for a slightly different area, so street-cell requests rarely hit the cache. If street-cell traffic grows, snap the requested area to a grid.

## What happens next
Once you approve this and [05-test-report.security.md](05-test-report.security.md):
1. I merge `feature/security` into `main`, which deploys, and check that the edge cache gives a `HIT` (criterion 44).
2. I create the Firewall rule with `vercel firewall rules add` and `publish`, then check it with a burst test and the normal-use browser check (criterion 45).
3. **You** replace `DATABASE_URL` in Vercel (Production and Preview) with the contents of `C:\Users\saika\uavert-web-database-url.txt`, and redeploy (or tell me and I'll redeploy).
4. I check criterion 47 in production: the acceptance check, plus Neon showing Vercel's connections as `uavert_web`.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
