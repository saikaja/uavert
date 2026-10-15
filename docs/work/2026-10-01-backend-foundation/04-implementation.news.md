# 4. Do the work: news by type of event, trending stories and police-report patterns

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Approved
**Builds:** [01-03-news.md](01-03-news.md) (approved 2026-10-15 14:49, "approve and yes toronto start and keep the existing news effect").

## What this step is
This records how the approved plan was built, step by step, with the evidence from real data.

## What was done
- **Branch:** `feature/news`, from `main` at `1542b52`. Steps T1–T5, plus the documents part of T6, each with tests and a commit. Production waits for your approval of this record and the test report.
- **Approach:** tests first for the classifier, trending and patterns. They use the real headlines and feeds of 2026-10-15, saved as fixtures.
- **Real data:** a temporary Neon branch, `news-check` (`br-sweet-sky-b5ql0jxo`), copied from `main`. On it I ran migration 010, `ingest news`, `build-scores` and the app. Production hasn't been touched.

## Plan steps

| # | Step | Result | Commit |
|---|---|---|---|
| T1 | Property-crime type; sports, "memorial" and earlier-year exclusions; kidnapping counts as violent; each type kept for its window; migration 010; property crime never scored | 13 new classifier and store tests, using real headlines | `d736786` |
| T2 | CityNews, Global News and Toronto Star feeds; one RSS parser; each feed its own source and step | On the real data copy: CityNews 15 stories read and 2 labelled; Global 10 and 1; Star 50 and 13. GDELT refused (HTTP 429) and was recorded as failed without affecting the others. 6 tests, including one feed failing. | `126b423` |
| T3 | Windows by type (`/news-events?window=by_type`); trending (`/news-trending`); removal of stored stories the rules now exclude | The real stories group into "Second Harvest" (5 stories, 3 outlets) and "bike-lane protests" (4 stories, 3 outlets). The removal step took out the 2 bad stories on the real data (cricket "rally", 2025 memorial). | `fd22c93` |
| T4 | Police-report patterns: `patterns.py`, stored by `build-scores`, `/crime-patterns`, `patterns` on `/neighbourhoods/{id}` | `build-scores` on the real data: "6 pattern(s) in police reports". Broadview North 7 break-ins against a usual 1.2, Playter Estates-Danforth 7 against 1.6, South Eglinton-Davisville 9 against 3.0, Golfdale-Cedarbrae-Woburn 7 against 2.0, Bendale South 5 against 1.1, Roncesvalles 9 against 3.1. No auto-theft pattern. | `1ace9bb` |
| T5 | "News and patterns" section; pattern line on the neighbourhood panel; rules page section | 13 of 13 headless Edge checks. Screenshots `news-1` to `news-3` in [screenshots/](screenshots/). | `94b8508` |
| T6 | README, acceptance checks `news-37` to `news-42`, E2E row 11 reworded and rows 48–51 | Acceptance check on the real data copy: **43 of 43**. Production deploy waits for your approval. | `ed9597b` |

## Files changed

| File | New / changed | Summary |
|---|---|---|
| `db/migrations/010_news_types_patterns.sql` | New | `property_crime` allowed; `crime_patterns` table |
| `src/uavert/sources/news.py` | Changed | `PROPERTY` words, sports and "memorial" exclusions, `EARLIER_YEAR`, `excluded()`, `classify(…, year)`, `RSS_FEEDS`, `parse_rss()`, `fetch_rss()` |
| `src/uavert/ingest/news.py` | Changed | Each type stored while inside its window; `rss_step()` for each feed; `relabel()` removes stored stories the rules now exclude |
| `src/uavert/ingest/steps.py`, `ingest/registry.py`, `config.py` | Changed | New feeds as steps and sources (with licence notes), feed addresses |
| `src/uavert/scoring/news.py` | Changed | `DISPLAY_DAYS`. Types outside `CAPS` are never scored. Reasons cite the story's own source. |
| `src/uavert/scoring/trending.py` | New | Significant words, groups (union-find), trending rule |
| `src/uavert/scoring/patterns.py` | New | Poisson chance and the pattern rule |
| `src/uavert/scoring/build.py`, `ingest/cli.py` | Changed | Patterns found and stored with each build; the count is printed |
| `src/uavert/api/live.py` | Changed | Only scored types are loaded for scoring; the source key is carried through |
| `src/uavert/api/routes/news.py`, `routes/patterns.py` (new), `routes/neighbourhoods.py`, `app.py` | Changed | `window=by_type`, `window_days`, `/news-trending`, `/crime-patterns`, `patterns` on neighbourhoods |
| `src/uavert/web/index.html`, `app.js`, `style.css`, `rules.html` | Changed | The section, the panel line and the rules page section |
| `tests/…` | New and changed | `test_trending.py`, `test_patterns.py`, `api/test_patterns_api.py`, new cases in `test_news.py` and `api/test_news_api.py`, 4 saved feeds. The seed data now also clears `crime_patterns`. |
| `README.md`, `scripts/acceptance_check.py`, `06-e2e-signoff.md` | Changed | As listed in T6 |

## Deviations from the plan
1. **Trending needs 3 shared words, not 2.**
   - The browser check on real data found the flag-arson story joined to the Star's six weekly break-in round-ups. They only shared "North York". This was a listed risk, with this fix.
   - With 3 words, the real events still group: Second Harvest has 5 stories from 3 outlets, and the bike-lane protests 4 from 3. CityNews's Second Harvest story ("catalytic convertor theft from Etobicoke food charity") now stays out, because it shares only 2 words with the others.
   - A regression test covers the North York case, and the rules page says "three".
2. **Removing stored stories the rules now exclude** (`relabel`, run first in each news collection).
   - This wasn't a separate plan step, but without it, the stories mislabelled before today stay listed for up to 7 days, and the plan's fixes wouldn't show.
   - It only **removes** clearly excluded headlines (sport, an earlier year, other regions). It doesn't change a stored type, because the summary that set it isn't stored.
   - On the real data it removed 2 stories. One test covers it.
3. **Kidnapping counts as a violent incident.** It wasn't in the plan's word list. Without it, "Seven charged in Toronto kidnapping investigation, ammo stolen…" became property crime because of "stolen".
4. **`/news-events` without `window`** keeps its parameters and behaviour, but its 24-hour list can now include `property_crime` stories (a new type value) and has a new `window_days` field. Nothing else changed in the response.

## Clean-up
I reviewed the diff (31 files; about 2,600 of the added lines are the 4 saved feeds).
- **One feed parser:** `parse_cbc_rss` and `fetch_cbc` are now thin wrappers kept for the existing tests and code.
- **Untrusted text:** news text is inserted with `textContent` and links pass `safeUrl`, as before.
- **Leftovers:** no debug code. One shell edit put two control characters into `sources/news.py` (a regex `\b` turned into a backspace). I caught it before committing, fixed it, and checked every tracked file for control characters: none.

## Follow-up ideas
- **Street-level patterns** (smaller than a neighbourhood). Broadview North and Playter Estates-Danforth are next to each other and may be one series.
- **Locating property-crime stories,** so they could appear on the map (still information only).
- **A favicon:** the site has never served one, and browsers log a 404 for it.
- **Star rate limits:** the Star answered "too many requests" after I fetched it about six times in an hour. Hourly collection should be fine; "Data collected" will show if it isn't.

## What happens next
Once you approve this and [05-test-report.news.md](05-test-report.news.md), production gets the change:
1. migration 010 on Neon `main`
2. `ingest news` and `build-scores`
3. merge and deploy
4. the acceptance check against https://uavert.vercel.app
5. delete the temporary branch

## Approval
- **Status:** Approved
- **Approved by:** Sai Kaja
- **Date:** 2026-10-15 15:12
- **User's response:** "approve and less just do 1 and 2 forget the rest" (approval of the news deploy; the rest refers to the security suggestions)
- **Revisions before approval:** none
