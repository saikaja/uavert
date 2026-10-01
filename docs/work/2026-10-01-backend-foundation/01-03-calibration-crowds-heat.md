# 1–3. Define, design and plan: fairer scores, crowds and extreme heat

**Task folder:** docs/work/2026-10-01-backend-foundation/  ·  **Date:** 2026-10-01  ·  **Status:** Pending approval
**Adds to / revises:** the approved definition and design revisions in this folder. The scoring change revises how scores are **scaled** (design and revisions 2–3, time of day). It doesn't change what is counted or how places are ranked. Covers phases 1–3 in one document, like the earlier additions.

## What this step is
Agree, before any code, how to fix scores that feel too harsh, and how to add big crowds and extreme heat.

## What was done

### 1. The harshness complaint
The user said ratings feel too harsh. Their example was the walk from Union Station to 125 Blue Jays Way scoring 84. Reproduced on 2026-10-01 (all day): the walk is 1,240 m, scores **80 "High"**, and its first reason is "3 homicides within about 250 m in the last 3 years".

| Block on the walk | Score today | Street incidents within ~250 m | People on foot / hour | Rank among Toronto blocks |
|---|---|---|---|---|
| 1 | 49 | 395 | 1,796 | top 51% |
| 2 | 70 | 388 | 1,736 | top 30% |
| 3 | 61 | 317 | 1,789 | top 39% |
| 4 | **80** | 390 | 1,589 | **top 20%** |

**Why it's harsh:**
- **Scores are rankings.** A block in the top 20% gets 80, which is "High". By design exactly a quarter of the city is "High" (1,437 of 5,748 blocks), whatever the actual level.
- **A walk reports its worst block.** That rule is unchanged and intended.
- **The first reason** leads with the rarest, most serious offence (homicides).

### 2. Options tested on the real scores

| Option | Share of the city lower / moderate / elevated / high | Walk (4 blocks) | City Hall |
|---|---|---|---|
| Today: rank among blocks | 25 / 25 / 25 / 26 % | 49 70 61 80 → **80** | 88 |
| A: same ranking, bands reshaped to 50/30/15/5 % | 49 / 30 / 15 / 5 % | 24 41 34 50 → **50** | 63 |
| B1: against a typical block, 25 points per doubling | 50 / 23 / 15 / 12 % | 24 46 37 60 → **60** | 74 |
| **B2: against a typical block, 20 points per doubling** (recommended) | **49 / 28 / 16 / 7 %** | 24 42 35 53 → **53** | **64** |

**Reading the table:**
- **"Typical block"** is the median Toronto block (per-person value 1.71). The walk's worst block is **2.7× typical**.
- **Neighbourhoods on B2:** they range from 0.4× typical (Lambton Baby Point, 0) to 3.9× (Yonge-Bay Corridor, 64). 79 neighbourhoods are lower, 73 moderate and 6 elevated; none is "High" on averages alone.

### 3. Data checked for crowds and heat (2026-10-01)
**City "Festivals & Events" feed** (JSON, 222 MB, 26,374 records; dataset page says licence "not specified"):
- 3,042 events in the first week of October, mostly small (exhibits, museums, workshops)
- **no attendance figures**, and coordinates usually blank, so addresses must be geocoded
- matching names like "festival" catches small events (a film festival at one cinema), but the feed does carry the big City events: **"Nuit Blanche 2026"** is listed and marked featured

**City "Air Conditioned and Cool Spaces (Heat Relief Network)"** (refreshed daily):
- **478 places:** 446 cooling locations, 12 cooling centres, 19 indoor pools and 1 wading pool
- each has an address, coordinates, and opening and closing times for every weekday

**Ticketmaster** was considered for game and concert schedules, but its terms prohibit "deriving revenues from the use or provision of the Ticketmaster API". The user chose **major venues + City festivals** instead.

**Weather alerts already carry Environment Canada's own risk colour** (yellow, orange or red), but today any "warning" sets the score to 90 ("High"). A routine yellow heat warning would turn the whole city "High".

## Definition

### Goal
Make scores mean something fixed and fair. Add the two general-safety factors the user chose: big crowds, and extreme heat with where to cool down.

### In scope
1. **Fairer scale.** Crime scores (street, street by hour, neighbourhood) are measured **against a typical Toronto block or neighbourhood**, at 20 points per doubling:
   - typical = 25
   - 2× typical = 45
   - 4× typical = 65
   - 8× typical = 85
   - capped at 0–100

   The bands keep their names and cut-offs (25, 50, 75), which now read: below typical, up to about 2.3× typical, up to about 5.3× typical, beyond that.
2. **Walks also show a typical score.** Walks still report the worst block, the "one bad stretch is never averaged away" rule. They also show `typical_score`, the median over the walk's length, so the panel can say "mostly moderate, worst block elevated".
3. **Calmer first reason.** A street block's first reason is its most **frequent** street offence. The most serious one, for example homicides, is still listed, second.
4. **Alerts use Environment Canada's colours:**
   - yellow → 40 (moderate)
   - orange → 65 (elevated)
   - red → 90 (high)
   - no colour: warning 65, watch or advisory 25, statement 0
5. **Extreme heat:**
   - load the City's cool spaces with their weekly hours
   - while a heat warning or advisory is active, scores near the place add a reason naming the **nearest cool space open at that time**, with distance and hours (for example "Heat warning in effect. Nearest cool space open now: Metro Hall, 400 m, until 7 pm")
   - when an hour is chosen, "open" is checked at that hour
6. **Big crowds:**
   - **Major venues,** a reviewed list of venues with capacity of 5,000 or more and their sources: blocks within about 500 m get a context reason, "Near Rogers Centre: can draw about 40,000 people on event days". **No score change**, because there are no schedules.
   - **Large City events,** a reviewed list of names (Nuit Blanche, Pride Parade, Toronto Caribbean Carnival / Grand Parade, Santa Claus Parade, New Year's Eve at Nathan Phillips Square, Canada Day celebrations, the Toronto Waterfront Marathon): matched against the City calendar for their actual dates and locations. On those dates, areas within about 1 km get a new **"crowds"** category of **35 (moderate)**, with a dated reason, "Nuit Blanche 2026 tonight: large crowds and road closures expected".

### Out of scope
- schedules for games and concerts (no licence-compatible source)
- extreme cold and warming centres
- the GTA (see [gta-expansion-notes.md](gta-expansion-notes.md))
- changing what is counted: offences, weights, foot traffic and homicide averaging all stay as they are

### Acceptance criteria (added to criteria 1–39)

**Fairer scale**
40. A unit test confirms the formula: 1× → 25, 2× → 45, 4× → 65, 8× → 85, 0.25× → 0, 64× → 100.
41. **The user's example:** walking Union Station → 125 Blue Jays Way all day scores **about 50–55, not "High"**. A reason states how the worst block compares with a typical block. The city-wide band shares are recorded (expected about 49/28/16/7 %).
42. **The order of places is unchanged.** Rank correlation between old and new scores is 1.0 for both blocks and neighbourhoods, so the fairness check numbers are unchanged.
43. **Later and emptier is still higher:** City Hall at 2 am scores higher than at 2 pm.
44. `/route-risks` returns `typical_score` and `typical_band`.
45. A street block's first crime reason is its most frequent offence group. Unit test.

**Alerts**

46. Alert scores follow the colour mapping above. Unit tests: yellow, orange and red warnings, a warning with no colour, an advisory, a statement.

**Extreme heat**

47. `ingest reference` (or a new `ingest heat` step) loads the cool spaces with hours and `collected_at` (expected 478).
48. With an active heat alert, a place's reasons name the nearest cool space open at that moment (or the chosen hour), with distance and closing time. Without a heat alert there is no such reason. Tested with a test heat warning and test cool spaces, including one that is closed at that hour.

**Crowds**

49. `data/major_venues.csv` lists each venue with address, capacity and a source. Blocks within about 500 m show the venue reason, and their score is unchanged. Test.
50. Large City events are matched by name against the calendar. On an event date, areas within about 1 km get `categories.crowds = 35` and a dated reason; on other dates they get nothing. Tests, plus a live check that Nuit Blanche 2026's date is found.
51. "Crowds" appears in every score's `categories`, combines like the others (highest wins), and the rules page explains it.

## Design

### Fairer scale
- **`scoring/crime.py`:** `relative_score(value, typical)` returns `clamp(25 + 20·log2(value / typical))`. The constant `POINTS_PER_DOUBLING = 20` is shown on the rules page.
- **Street scores** (`build.cell_scores`): typical = the median all-day per-person value over all blocks. **Hourly scores** use the **same all-day typical**, so night hours rise naturally. The time-of-day ranking across all hours is replaced by this.
- **Neighbourhood scores:** typical = the median weighted rate of the 158 neighbourhoods.
- **Reasons:** street blocks add "About 2.7× the reported street crime per person of a typical Toronto block"; neighbourhoods add "About 3.9× a typical Toronto neighbourhood".
- **Stored values:** `per_person_value` and `weighted_rate` are already stored, so only the score columns are recomputed. **No new data is needed.**
- **Walk `typical_score`:** the length-weighted median of the block scores along the walk.

### Alerts
`scoring/alerts.alert_level` maps colour first, then type, as above.

### Extreme heat
- **Data:** the City heat relief CSV goes into a new table `cool_spaces` (name, type, address, point, `hours` jsonb by weekday, `collected_at`), as source `toronto_cool_spaces` under the Open Government Licence – Toronto.
- **Refresh:** loaded by `ingest reference` and refreshed daily with the GitHub Actions full run.
- **At request time:** if an active alert's name contains "heat", find the nearest cool space within 3 km that is open at the moment (or the chosen hour), using a spatial index (KNN), and add the reason under the alert category.

### Crowds
- **Venues:** `data/major_venues.csv` (name, address, capacity, source URL, retrieval date) for venues with capacity of 5,000 or more:
  - Rogers Centre
  - Scotiabank Arena
  - BMO Field
  - Budweiser Stage
  - Coca-Cola Coliseum
  - Enercare Centre / Exhibition Place
  - Nathan Phillips Square (outdoor)

  Capacities come from each venue's official page or Wikipedia, recorded per row. Addresses are geocoded once (saved lookups), and the `venues` table is loaded by `ingest reference`.
- **Large City events:** `data/large_city_events.csv` holds the reviewed name patterns (Nuit Blanche, Pride Parade, Caribbean Carnival, Santa Claus Parade, New Year's Eve, Canada Day, Waterfront Marathon). A new daily ingest step reads the City feed, keeps matching events with dates in the next 60 days, geocodes their location address (or uses the pattern's default location when it's blank, for example Nuit Blanche → City Hall), and stores them in `crowd_events` (name, dates, point, `collected_at`).
- **Scoring:** a new `crowds` category. The event floor is 35 within 1 km on its dates (Toronto time, all day); venue context gets a reason only. `combine.CATEGORIES` gains "crowds".

### Review checklist

| Area | Finding |
|---|---|
| **Compatibility** | Scores change scale. Fields are added only (`categories.crowds`, `typical_score`, `typical_band`), and every `/api/v1` path is unchanged. The ranking order is unchanged, so the fairness check is unaffected. |
| **Edge cases** | **Typical value of 0:** impossible, since the median per-person value is above 0. **Very small values:** capped at 0. **Events without a location:** use the pattern's default location, or are skipped and logged. **Overnight cool-space hours:** the hours are same-day; anything else is treated as closed. **No heat alert:** no heat reason. |
| **Performance** | Rescaling is part of `build-scores` (seconds). The nearest cool space is one indexed query, run only during heat alerts. The 222 MB events feed is read in a scheduled job, never on a request. |
| **Security** | Event names come from the City feed and are shown as text only (the map already escapes text). Venue sources are written by us. |
| **Testability** | Pure functions for the formula, alert levels, opening hours and event-date matching; API tests with test alerts, cool spaces and events. |

### Alternatives considered
- **Reshaping the ranking into 50/30/15/5 % (option A).** Similar numbers, but it still forces a fixed share of the city into each band, and gives no plain meaning ("2.7× typical").
- **25 points per doubling (B1).** Keeps more blocks "High" (12 %), and the example walk scores 60.
- **Averaging the walk instead of taking its worst block.** That would hide a bad stretch. Instead we keep the worst block and add `typical_score`.
- **Ticketmaster for event schedules.** Its terms prohibit revenue-generating use, so it was rejected.

### Risks

| Risk | How it's reduced |
|---|---|
| "Typical" moves when data is reloaded | It is recomputed at each build and shown on the rules page with its date. Over time it reflects Toronto as a whole, which is the point. |
| The large-event list misses an event, or a name changes | The list is reviewed data in `data/`, easy to extend. Unmatched events simply don't appear. |
| Venue capacities are approximate | They are labelled "about", with the source per row, and don't change scores. |
| The City feed's licence is "not specified" on its page | We use event names, dates and locations only, with attribution, under the portal's Open Government Licence – Toronto. Confirm before public launch (the same note as the traffic counts). |

## Plan

| # | What | Done when |
|---|---|---|
| C1 | Fairer scale: formula, street / hourly / neighbourhood rescaling, ratio reasons, calmer first reason, walk `typical_score` | Tests for criteria 40, 42–45; rebuild; live check of criterion 41 (Union → 125 Blue Jays Way); band shares recorded |
| C2 | Alert colours | Tests for criterion 46 |
| C3 | Extreme heat: cool spaces loaded, nearest-open reason during heat alerts | Tests for criteria 47–48; 478 loaded |
| C4 | Crowds: venues list, large-event list and ingest, `crowds` category, rules page | Tests for criteria 49–51; Nuit Blanche 2026 found live |
| C5 | Web map: "mostly … , worst block …" on walks; crowds and heat in panels; rules page sections | Run by hand; screenshot |
| C6 | Tests again, deploy to Vercel, update records and the phase 6 checklist | Full suite; acceptance check 22/22 on local and hosted; documents updated |

## What happens next
Once this is approved, I build C1–C6 on `feature/backend-foundation`, deploy to Vercel, and give you the before-and-after numbers. Your phase 6 checklist then gets the new rows.

## Approval
- **Status:** Pending approval
- **Approved by:**
- **Date:**
- **User's response:**
- **Revisions before approval:** none
