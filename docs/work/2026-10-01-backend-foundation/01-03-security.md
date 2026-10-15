# 1–3. Define, design and plan: rate limits, edge caching and a read-only database user

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Adds to:** [01-03-solidify.md](01-03-solidify.md) (hosting) and the security review in [02-design.md](02-design.md). This document covers phases 1–3 in one, as the workflow allows for a contained addition.

## What this step is
This document agrees how the public API is protected against abuse, and how the website's access to the database is reduced to what it needs. One approval covers the definition, design and plan.

## What was done
- **The request.** Sai asked, on 2026-10-15: "should we protect our api's because they are public also are there any other security things we should consider". I listed 8 findings. Sai replied: "just do 1 and 2 forget the rest":
  1. rate limits and caching
  2. a read-only database user for the website
- **Why not a login or API key.** The map runs in the visitor's browser and calls the same API, so any key would be visible in the page. All the data is public, and there are no accounts. The real risks are cost and availability, and abuse of the free services the API passes requests to. Sai agreed with this approach.
- **What the API does today** (checked 2026-10-15):
  - **Rate limits:** only address and walk lookups are limited (30 a minute), and that limit lives in each server instance's memory. Vercel runs many short-lived instances, so it barely holds. It also uses `request.client.host`, which hasn't been confirmed to be the visitor's IP address on Vercel.
  - **Unlimited endpoints:** every other endpoint has no limit. `/api/v1/neighbourhoods` returns 164 KB and takes about 1 s of database work on each call.
  - **No caching:** two requests in a row both returned `Cache-Control: public, max-age=0, must-revalidate` and `X-Vercel-Cache: MISS`. Every request reaches the database.
  - **Database user:** the website connects as `neondb_owner`, the database owner, which can change or delete anything.
  - **What the website writes:** I searched the API code. It only writes to `geocode_cache` and `route_cache` (saved address and route answers). Everything else is read-only; the hourly and daily refresh writes from GitHub Actions, with its own connection.
- **Vercel's options** (`vercel firewall status`, 2026-10-15):
  - **Plan:** Hobby. "Bypass: Requires Pro or Enterprise". The Firewall shows "Not configured".
  - **Rate limiting:** Vercel's docs (rate-limiting page, updated 2026-06-16) allow **1 rate-limit rule per project on Hobby**, fixed window, keyed by IP, with 1 million allowed requests a month included.
  - **Setup:** `vercel firewall rules add … --action rate_limit` can create it from the command line.
- **Neon roles.** Roles created in Neon's console or API are made members of `neon_superuser`, which has broad rights. So the read-only role is created with SQL (`CREATE ROLE … LOGIN`), which gives it no rights beyond those granted.

## Definition

### Goal
1. Nobody can run up database usage or get the site blocked by flooding the API.
2. Repeated requests are answered from Vercel's edge cache instead of the database.
3. The website can read the data, but can't change or delete it.

### In scope
1. **Edge caching:** successful `GET` responses under `/api/v1/` (except `/health`) are cached by Vercel for 5 minutes, and may be served up to 5 more minutes while a fresh copy is fetched. Browsers don't keep them.
2. **A Vercel Firewall rate-limit rule:** at most **120 requests per 60 seconds per IP address** to `/api/`. Beyond that, Vercel answers 429 itself, before the app or the database is touched.
3. **A read-only database user, `uavert_web`,** created with SQL on Neon `main` (and on the `test` branch for the tests). It can read every table and only write the two saved-lookup tables. The website on Vercel uses it. GitHub Actions and the local command line keep the owner.
4. **Migration 011** grants those rights, including on tables added later.

### Out of scope
These are Sai's decision ("forget the rest"):
- security headers
- a CDN integrity check
- the dependency audit
- changing the database password

Also out:
- **Changing the existing in-app limit** on address and walk lookups. It stays as an extra layer.
- **A login or private site.**

### Acceptance criteria (added to criteria 1–42)
43. **Caching.** A successful API `GET` carries `Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=300`. Errors (4xx and 5xx) and `/health` carry no caching header. API tests check both.
44. **Edge cache in production.** Requesting `/api/v1/neighbourhoods` twice in a row returns `X-Vercel-Cache: MISS`, then `HIT` (or `STALE`), and the second answer is much faster.
45. **Rate limit in production.** `vercel firewall status` shows the rule. A burst of 130 quick requests to a cheap endpoint from this laptop gets HTTP 429 after about 120. Normal use of the map, run as the browser check, gets no 429.
46. **Read-only user on the test branch.** A test connects as `uavert_web` and checks that it:
    - can read neighbourhoods, scores, news and patterns
    - can save to `geocode_cache` and `route_cache`
    - is refused `INSERT INTO incidents`, `DELETE FROM neighbourhoods`, `UPDATE neighbourhood_scores` and `CREATE TABLE` ("permission denied")
47. **The website works as `uavert_web`.** Locally, the full `acceptance_check.py` (43 checks, including address searches that save to the cache) passes with the app connected as `uavert_web` to Neon `main`. After the Vercel switch, the production acceptance check passes, and Neon shows Vercel's connections logged in as `uavert_web`.

## Design

### Caching (`api/app.py` middleware)
- **Header:** after each response, if the request is a `GET` under `/api/v1/` other than `/health`, and the status is 200, set `Cache-Control: public, max-age=0, s-maxage=300, stale-while-revalidate=300`.
  - `s-maxage` is read only by Vercel's CDN.
  - `max-age=0` keeps browsers asking for fresh answers.
- **Cache key:** Vercel keys its cache on the full URL with the query string, so each hour, bounding box and address is cached separately.
- **What changes for visitors:**
  - "Data collected" and live conditions (air quality, alerts, news) can be up to 5 to 10 minutes behind the database. They're collected hourly anyway.
  - A repeated address or walk check, and the city map, come back from the edge in milliseconds.
- **Not cached:** error responses. A 429 or 502 must not be repeated to other visitors.

### Rate limit (Vercel Firewall, configured with the CLI)

```
vercel firewall rules add "API rate limit" \
  --condition '{"type":"path","op":"pre","value":"/api/"}' \
  --action rate_limit --rate-limit-requests 120 --rate-limit-window 60 --rate-limit-keys ip --yes
vercel firewall publish
```

- **Why 120 a minute:**
  - Opening the page makes 6 API calls.
  - Each pan or zoom at street level makes 1 call, debounced by 250 ms.
  - Each time change makes 2 to 3 calls.
  - Heavy normal use is about 30 to 60 a minute, so 120 leaves room, while a script at 5 a second is cut off within 30 seconds.
- **Counting:** it counts requests before the cache, so cached answers count too. The limit is about flooding, not cost per request.
- **Reversible:** `vercel firewall rules` can disable or remove it at any time, without a deploy.

### Read-only database user
1. **Create on Neon `main`, as the owner, with SQL:** `CREATE ROLE uavert_web LOGIN PASSWORD '<random 32 characters>'`. A local script does this. It generates the password, and writes the connection string to `C:\Users\saika\uavert-web-database-url.txt`, outside the repository. The password is never printed into this conversation.
2. **Migration 011** (grants only if the role exists, so local and other databases are unaffected):

   ```sql
   GRANT USAGE ON SCHEMA public TO uavert_web;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO uavert_web;
   GRANT INSERT, UPDATE ON geocode_cache, route_cache TO uavert_web;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO uavert_web;
   ```

3. **Same on the Neon `test` branch** for criterion 46. Its URL goes in the local `.env` as `TEST_WEB_DATABASE_URL`; `.env` is not in git.
4. **The switch on Vercel (your step).** Replace `DATABASE_URL` for Production and Preview with the contents of that file. Earlier this session, Claude was blocked from writing Vercel secrets, so you'd do it in the Vercel dashboard (Settings → Environment Variables) or with `vercel env`. A redeploy picks it up. **To undo:** put the previous value back.

### Review checklist

| Area | Finding |
|---|---|
| Correctness | **Caching** only affects successful GETs; no endpoint depends on per-visitor state (no cookies or accounts). **The read-only role** has every right the website needs: read, plus saving lookups (confirmed by searching all writes in `api/` and `sources/`). |
| Security | **The rate limit** runs at Vercel's edge using the IP Vercel sees, which a client can't fake with headers. **The read-only role** limits what a leaked website password or a bug can do. **The role's password** stays out of git and out of this conversation. |
| Performance | **Edge caching** removes most database work for repeated requests. **The rate limit** adds no latency to the app. |
| Compatibility | **Response bodies** don't change. **Local `serve`** gets the same headers, which do nothing without a CDN. **The hourly refresh** keeps writing as the owner. |
| Cost | **Vercel Hobby:** 1 rule and 1 million allowed requests a month included; the site's traffic is far below that. **Neon:** one more role, no cost. |

### Alternatives considered
1. **A rate limit in the app, stored in the database:** every request would write to the database, which adds the very load we're trying to avoid. And it runs after the request has already reached a function. Rejected in favour of the Firewall.
2. **An API key:** visible in the page. Rejected (see "What was done").
3. **Snapping the map area for street cells to a grid,** so more requests hit the cache: it would make some requests cross the 25 km² limit at the edge of zoom 14. Not needed with the rate limit. A follow-up if cell traffic grows.

### Risks

| Risk | How it's reduced |
|---|---|
| Visitors behind one shared IP (an office or school) together exceed 120 a minute | Unlikely at today's traffic. The rule can be raised or switched to log-only with one command. |
| Cached live data looks up to about 10 minutes old | Collection is hourly anyway. "Data collected" shows the real times. |
| The website lacks a right it needs after the switch | The full acceptance check runs locally as `uavert_web` before you switch Vercel. The switch can be undone by restoring the old value. |
| Future tables need rights too | Default privileges grant read on new tables. A table the website must write would need its own grant in its migration; noted in the migration. |

## Plan
Branch `feature/security` from `main`. Each step has tests and a commit.

| # | What | Files | Tests | Done when |
|---|---|---|---|---|
| T1 | Caching headers | `api/app.py` | Criterion 43 (API tests: a 200 is cached, a 422 and `/health` are not) | Tests pass |
| T2 | Read-only user: script to create the role (test branch, then Neon `main`, after your approval of this document); migration 011; test as `uavert_web` | `scripts/create_web_role.py`, `db/migrations/011_web_role.sql`, `tests/test_web_role.py` | Criterion 46 on the test branch; criterion 47 locally against `main` | Both pass |
| T3 | README, acceptance check (`Cache-Control` header), E2E row; build and test records | `README.md`, `scripts/acceptance_check.py`, `06-e2e-signoff.md` | Full suite | Everything passes |
| T4 | After your approval of phases 4–5: run migration 011 on Neon `main`, merge and deploy, create the Firewall rule, check criteria 44 and 45. Then **you** switch Vercel's `DATABASE_URL` and I check criterion 47 in production. | — | Acceptance check against production; the burst test; Neon connection check | All pass |

## What happens next
Once this is approved, I build T1–T3, including creating `uavert_web` on the test branch and on Neon `main`. Creating the role on `main` changes nothing until the website uses it. Then I write `04-implementation.security.md` and `05-test-report.security.md` for your approval, before the production steps in T4.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
