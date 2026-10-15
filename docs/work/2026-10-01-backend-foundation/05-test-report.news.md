# 5. Verify the work: news by type of event, trending stories and police-report patterns

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-15  ·  **Status:** Pending approval
**Verifies:** [01-03-news.md](01-03-news.md), criteria 36–42, built in [04-implementation.news.md](04-implementation.news.md).

## What this step is
This is the evidence that each new acceptance criterion is met, and that nothing that worked before has broken, scores above all.

## What was done
- **Automated tests:** the full suite.
- **Real data:** on the temporary Neon branch `news-check` (a copy of the real data) I ran `ingest news` and `build-scores`. I compared every stored score with production, ran `acceptance_check.py` against the local app, and drove the page in headless Edge.
- **Review:** went through the diff on correctness, readability, architecture, security and performance.

## Automated checks

| Check | Command | Result (quoted) |
|---|---|---|
| Full test suite | `python -m pytest -q` | "286 passed in 78.18s" (exit code 0) |
| Acceptance check, local app on real data | `python scripts/acceptance_check.py http://127.0.0.1:8012` | "43 of 43 checks passed" |
| Browser check (headless Edge, CDP) | scratch script, 13 checks | "13 of 13 browser checks passed" |
| Scores unchanged | every stored neighbourhood and street score, hourly scores and reasons: real data copy rebuilt with the new code, against production built with the old code | "158 158 identical", "5748 5748 identical" |

**Compared with the baseline:** 250 tests passed on `main` this morning; there are now 286 (36 new), all passing.

## Acceptance criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 36 | `property_crime` for break-ins, thefts and arson; sport and the 2025 memorial excluded; the bike-lane protest stays a protest | `test_types_of_event_from_real_headlines`: 10 real headlines. `test_real_feeds_label_the_days_events`: across the 4 saved feeds, at least 4 bike-lane protests, at least 4 Second Harvest property-crime stories, and no "Sixers". `test_property_words_never_outrank_violence`. | Passed |
| 37 | `window=by_type`: protests 2 days, violent 7, property 60; without `window`, as before | API test `test_news_events_by_type_use_each_types_window`: a 3-day protest, an 8-day stabbing and a 70-day break-in are left out; the others are kept with their `window_days`. `window=all` returns 422. The existing `since_hours` tests still pass. Acceptance check `news-37`: "22 stories by type: protest 4, violent_incident 6, property_crime 12". | Passed |
| 38 | New feeds collected, each a source with dates; one failing leaves the others | `test_each_real_feed_parses` (20, 15, 10 and 50 items). `test_one_feed_failing_leaves_the_others`: CityNews times out, Global's stories are still stored, and the statuses are failed and ok. Real run: all three feeds stored stories. Acceptance check `news-38`. | Passed |
| 39 | Trending: at least 3 stories from at least 2 outlets in 3 days; real events grouped without mixing | `test_trending.py`, 6 tests on the real headlines: Second Harvest 5 stories from 3 outlets, bike lanes 4 from 3, never mixed. The Star's one-outlet round-ups don't trend, nor do old stories, and the "North York" case stays separate. Acceptance check `news-39`: "2 trending: 5 stories/3 outlets…; 4 stories/3 outlets…". | Passed |
| 40 | Patterns stored by `build-scores`, listed with counts, usual level and dates; a spike that passes, one too small, one that could be chance; Broadview North found live | `test_patterns.py` (5 tests) and `api/test_patterns_api.py` (2 tests). Real build: "6 pattern(s) in police reports", Broadview North first (7 against 1.2, chance 0.0002). Acceptance check `news-40`. | Passed |
| 41 | No score changes | Unit test: a fresh property story on a cell scores 0. API test: a located property story next to Test East leaves its news score at 0, and a pattern leaves its crime score at the seeded 20. **Real data:** all 158 neighbourhood rows and 5,748 street rows are identical to production, including hourly scores and reasons. | Passed |
| 42 | Web: three parts with windows or dates; a pattern opens its neighbourhood; the panel shows the pattern; no console errors; no sideways scrolling | Browser checks: headings "Trending / Recent / Patterns in police reports"; "Protests (last 2 days) / Violent incidents (last 7 days) / Property crime (last 60 days)"; "Show all" works; the pattern opens Broadview North and its panel shows "Pattern in police reports"; phone width fits; the rules page section exists; no console errors (see below). Screenshots `news-1-section.png`, `news-2-pattern-panel.png`, `news-3-phone.png`. | Passed |

Earlier criteria still hold: the same 43-of-43 run covers checks 1–35, the odds and the trends.

## Real-app checks
- **Collection on the real data copy:**
  - "news_citynews: 15 stories read, 2 labelled"
  - "news_global: 10 stories read, 1 labelled"
  - "news_star: 50 stories read, 13 labelled"
  - GDELT: "HTTP 429", recorded as failed; the others were unaffected
  - a second run an hour later: the Star also returned 429 (see the code review)
- **Build:** "Scored 158 neighbourhoods and 5748 street cells from 62,719 distinct crime events; 6 pattern(s) in police reports."
- **Trending on the page:**
  - "29-year-old man arrested after Thanksgiving theft at Second Harvest charity: Toronto police · Property crime · 5 stories from 3 outlets since Oct 14"
  - "Cyclists continue protest as bike lane removal work underway in Etobicoke · Protest · 4 stories from 3 outlets since Oct 14"

## Code review findings

| # | Finding | Action |
|---|---|---|
| 1 | Trending joined unrelated stories that only shared a place ("North York") | Fixed: 3 shared words. Regression test added (deviation 1 in the build record). |
| 2 | Stories mislabelled before today would stay listed for up to 7 days | Fixed: excluded stories are removed at each collection (deviation 2) |
| 3 | `signal_strength` would have failed on a `property_crime` story (no cap for that type) | Fixed in two places: scoring only loads protest and violent-incident stories, and `signal_strength` returns 0 for any other type. Tested. |
| 4 | News reasons named their source as CBC or GDELT only | Fixed: each story carries its own source key |
| 5 | The test seed deleted neighbourhoods while `crime_patterns` still pointed at them | Fixed: the seed clears `crime_patterns` first |
| 6 | **Security:** feed text is untrusted | Only headline, summary, link and time are read. Links must be http(s). Text is inserted with `textContent`. New endpoints are read-only, and `window` is validated (422 otherwise). |
| 7 | **Performance:** trending is computed per request | It handles about 30 stories now and at most a few hundred in 7 days; the test with 21 headlines runs in milliseconds. Patterns are one pass over the events already loaded by the daily build. |
| 8 | Toronto Star rate limits (429 after about six fetches in an hour while testing) | Hourly collection is one fetch an hour. A failure is shown in "Data collected", and earlier stories are kept. Listed as a follow-up to watch. |
| 9 | Browsers log a 404 for `/favicon.ico` | It predates this change: production has never served one (checked: 404). It's not counted as an error of this change, and is a follow-up. |

## Could not verify
These go to your test list:
- **The hosted site:** production gets this only after your approval (rows 48–51).
- **A real phone:** only a 390 px phone-sized window was checked.
- **A full hour of collection in production,** including whether the Star's limits allow hourly fetching. The first production runs will show it in "Data collected".
- **Whether the trending groups and patterns make sense to you** (rows 48 and 49).

## What happens next
Once you approve this and the build record:
1. migration 010 on Neon `main`, then `ingest news` and `build-scores`
2. merge `feature/news` into `main`, which deploys
3. acceptance check against production
4. delete the temporary branch `news-check`

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
