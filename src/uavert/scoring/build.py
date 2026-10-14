"""`uavert build-scores`: compute crime scores for every neighbourhood and street cell and store them."""

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from statistics import median
from zoneinfo import ZoneInfo

import asyncpg
import h3

from uavert.config import get_settings
from uavert.freshness import source_dates
from uavert.ingest.reference import load_excluded_places, load_offence_map
from uavert.scoring import crime, fairness, odds, trends
from uavert.scoring.combine import Reason
from uavert.scoring.events import count_once
from uavert.sources.tps import CrimeYear

NEIGHBOURHOOD_YEAR = 2025
HOMICIDE_FIRST_YEAR = NEIGHBOURHOOD_YEAR - crime.HOMICIDE_YEARS + 1  # 2023
STREET_WINDOW_DAYS = 365
TORONTO_TZ = ZoneInfo("America/Toronto")

# Which dataset a reason about each offence group cites.
GROUP_SOURCE = {"homicides": "tps_homicides", "shootings": "tps_shootings",
                "thefts from vehicles": "tps_ncr", "bicycle thefts": "tps_ncr"}
SINGULAR = {"homicides": "homicide", "shootings": "shooting", "firearm offences": "firearm offence",
            "robberies": "robbery", "assaults": "assault", "break-ins": "break-in", "auto thefts": "auto theft",
            "thefts over $5,000": "theft over $5,000", "thefts from vehicles": "theft from a vehicle",
            "bicycle thefts": "bicycle theft"}


def counted(n: int, group: str) -> str:
    return f"{n:,} {SINGULAR.get(group, group) if n == 1 else group}"


@dataclass(frozen=True)
class Event:
    event_id: str
    source_key: str
    csi_offence_key: str
    weight: float
    group: str
    premises_type: str | None
    occurred_at: datetime
    hood_external_id: str | None
    h3: str | None


async def load_events(conn: asyncpg.Connection, edition: str) -> list[Event]:
    offence_map = load_offence_map()
    excluded = load_excluded_places()  # incidents inside the two jails (01-03-odds.r2.md)
    rows = await conn.fetch(
        "SELECT i.event_id, i.source_key, i.ucr_code, i.ucr_ext, i.csi_offence_key, w.weight, i.premises_type,"
        " i.occurred_at, i.hood_external_id, i.h3::text AS h3, ST_X(i.geom) AS lon, ST_Y(i.geom) AS lat"
        " FROM incidents i JOIN csi_weights w ON w.edition = $1 AND w.offence_key = i.csi_offence_key",
        edition,
    )
    events = [
        Event(r["event_id"], r["source_key"], r["csi_offence_key"], float(r["weight"]),
              offence_map.resolve(r["source_key"], r["ucr_code"], r["ucr_ext"]).group_label,
              r["premises_type"], r["occurred_at"], r["hood_external_id"], r["h3"])
        for r in rows if not crime.at_excluded_place(r["premises_type"], r["lon"], r["lat"], excluded)
    ]
    return count_once(events, event_id=lambda e: e.event_id, weight=lambda e: e.weight)


def neighbourhood_scores(events: list[Event], hoods: list[dict], weights: dict[str, float], ncr_extra: dict[str, tuple[str, str]], used: dict,
                         severities: dict[str, str] | None = None) -> dict[int, dict]:
    """Calendar-year CSI-weighted rate per 100,000 residents, ranked across the city, with the odds per resident.

    `hoods`: dicts with id, external_id, population, counts (published counts for the year).
    `ncr_extra`: published count name -> (csi_offence_key, group) for offences the incident data lacks.
    `severities`: CSI offence -> severity level (default: from the offence map).
    """
    severities = severities or load_offence_map().severities()
    by_hood: dict[str, Counter] = defaultdict(Counter)  # (csi_key, group) -> count (homicides: yearly average)
    homicides: Counter = Counter()  # hood -> homicide events over the averaging years
    for e in events:
        if not e.hood_external_id:
            continue
        year = e.occurred_at.astimezone(TORONTO_TZ).year
        if e.source_key == "tps_homicides":
            if HOMICIDE_FIRST_YEAR <= year <= NEIGHBOURHOOD_YEAR:
                by_hood[e.hood_external_id][(e.csi_offence_key, e.group)] += 1 / crime.HOMICIDE_YEARS
                homicides[e.hood_external_id] += 1
        elif year == NEIGHBOURHOOD_YEAR:
            by_hood[e.hood_external_id][(e.csi_offence_key, e.group)] += 1
    for h in hoods:
        for name, key in ncr_extra.items():
            by_hood[h["external_id"]][key] += h["counts"].get(name, 0)

    rates, details, levels = {}, {}, {}
    for h in hoods:
        counts = by_hood[h["external_id"]]
        pop = h["population"] or 0
        per_offence = Counter()
        for (key, _group), c in counts.items():
            per_offence[key] += c
        rates[h["id"]] = crime.weighted_rate(per_offence, weights, pop)
        levels[h["id"]] = odds.by_level(per_offence, severities)
        groups = defaultdict(lambda: {"count": 0, "weighted": 0.0})
        for (key, group), c in counts.items():
            groups[group]["count"] += c
            groups[group]["weighted"] += c * weights[key]
        details[h["id"]] = {g: {"count": v["count"], "rate_per_100k": v["count"] / pop * 100_000 if pop else 0.0,
                                "weighted": v["weighted"]} for g, v in groups.items()}

    medians = {g: median(d.get(g, {"rate_per_100k": 0.0})["rate_per_100k"] for d in details.values())
               for g in {g for d in details.values() for g in d}}
    typical = median(rates.values())
    scores = {k: crime.relative_score(v, typical) for k, v in rates.items()}
    toronto = {level: sum(c[level] for c in levels.values()) for level in odds.LEVELS}
    toronto_population = sum(h["population"] or 0 for h in hoods)
    out = {}
    for h in hoods:
        d = details[h["id"]]
        top = sorted(d.items(), key=lambda kv: -kv[1]["weighted"])[:2]
        ratio = crime.times_typical(rates[h["id"]], typical)
        reasons = [Reason("crime", f"About {ratio:.1f}× the reported crime per resident of a typical Toronto neighbourhood "
                                   f"({NEIGHBOURHOOD_YEAR}, weighted by seriousness)",
                          source_key="tps_mci", value=round(ratio, 2), as_of=str(NEIGHBOURHOOD_YEAR),
                          collected_at=used.get("tps_mci", {}).get("collected_at")).to_dict()]
        for g, v in top:
            if not v["count"]:
                continue
            src = GROUP_SOURCE.get(g, "tps_mci")
            if g == "homicides":
                n = homicides[h["external_id"]]
                text = (f"{counted(n, g)} in {HOMICIDE_FIRST_YEAR}-{NEIGHBOURHOOD_YEAR} ({crime.HOMICIDE_YEARS}-year average; "
                        f"{v['rate_per_100k']:,.1f} a year per 100,000 residents; Toronto median {medians[g]:,.1f})")
                value, as_of = n, f"{HOMICIDE_FIRST_YEAR}-{NEIGHBOURHOOD_YEAR}"
            else:
                text = (f"{counted(round(v['count']), g)} reported in {NEIGHBOURHOOD_YEAR} "
                        f"({v['rate_per_100k']:,.0f} per 100,000 residents; Toronto median {medians[g]:,.0f})")
                value, as_of = round(v["count"]), str(NEIGHBOURHOOD_YEAR)
            reasons.append(Reason("crime", text, source_key=src, value=value, as_of=as_of,
                                  collected_at=used.get(src, {}).get("collected_at")).to_dict())
        out[h["id"]] = {"weighted_rate": rates[h["id"]], "crime_score": scores[h["id"]], "reasons": reasons,
                        "details": {"year": NEIGHBOURHOOD_YEAR, "groups": d, "toronto_median_rate_per_100k": medians,
                                    "odds": odds.odds(levels[h["id"]], h["population"], toronto, toronto_population,
                                                      NEIGHBOURHOOD_YEAR)}}
    return out


def add_trends(hood_rows: dict[int, dict], rows: list[CrimeYear], used: dict) -> None:
    """Attach the 10- and 5-year trends (01-03-trends.md) to each neighbourhood's details. Rows are keyed by
    neighbourhood id; with no yearly figures loaded, nothing is added."""
    if not rows:
        return
    if not any(r.year == NEIGHBOURHOOD_YEAR for r in rows):
        print(f"  no trends: the yearly figures don't include {NEIGHBOURHOOD_YEAR} yet (reload the reference data)")
        return
    per_hood, toronto = trends.trends(rows, NEIGHBOURHOOD_YEAR)
    source = {"source_key": "tps_ncr", "collected_at": used.get("tps_ncr", {}).get("collected_at")}
    for hid, r in hood_rows.items():
        if t := per_hood.get(str(hid)):
            r["details"]["trend"] = t | {"toronto": toronto} | source


def typical_block_reason(ratio: float, f: crime.FootTraffic, busy: bool, city_median: float, as_of: str,
                         collected_at: str | None) -> dict:
    """How the block compares with a typical Toronto block, and the foot traffic the comparison allows for."""
    compared = f"About {ratio:.1f}× the reported street crime per person of a typical Toronto block"
    if f.estimated:
        foot = f"; no foot-traffic count nearby, so the Toronto median of about {city_median:,.0f} people an hour is used"
    else:
        years = str(f.first_date.year) if f.first_date.year == f.last_date.year else f"{f.first_date.year}-{f.last_date.year}"
        plural = "s" if f.counts_used != 1 else ""
        counted = f"{f.counts_used} City of Toronto count{plural}, {years}"
        foot = (f"; busy area with about {f.per_hour:,.0f} people an hour on foot ({counted}), which the score allows for"
                if busy else f", allowing for about {f.per_hour:,.0f} people an hour on foot nearby ({counted})")
    return Reason("crime", compared + foot, "tps_mci", value=round(ratio, 2), as_of=as_of,
                  collected_at=collected_at).to_dict()


def local_hour(e: Event) -> int | None:
    """The Toronto hour an incident happened; None for homicides, which are published without a time."""
    return None if e.source_key == "tps_homicides" else e.occurred_at.astimezone(TORONTO_TZ).hour


def cell_scores(events: list[Event], cells: dict[str, int], hood_names: dict[int, str], used: dict,
                traffic: list[tuple[str, float, date]] | None = None,
                activity: list[float] | None = None) -> dict[str, dict]:
    """Street score per H3 cell: the last 12 months of street incidents, per person on foot nearby.

    `cells`: h3 -> neighbourhood id for every cell in the grid.
    `traffic`: (h3, pedestrians per hour, count date) for each counted location since FOOT_TRAFFIC_SINCE.
    `activity`: people out at each hour 0-23 relative to the daytime average (default: 1.0 every hour).
    """
    street = [e for e in events if e.h3 and crime.counts_on_street(e.premises_type)]
    if not street:
        raise ValueError("No located street incidents to score. Run `uavert ingest crime` first.")
    newest = max(e.occurred_at for e in street)
    since = newest - timedelta(days=STREET_WINDOW_DAYS)
    homicides_since = newest - timedelta(days=365 * crime.HOMICIDE_YEARS)

    def is_homicide(e: Event) -> bool:
        return e.source_key == "tps_homicides"

    def contribution(e: Event) -> float:
        """Homicides count 1/3 for 3 years; everything else fades over the last 12 months."""
        if is_homicide(e):
            return e.weight / crime.HOMICIDE_YEARS
        return e.weight * crime.recency_weight((newest - e.occurred_at).total_seconds() / 86400)

    street = [e for e in street if e.h3 in cells and e.occurred_at > (homicides_since if is_homicide(e) else since)]

    own = dict.fromkeys(cells, 0.0)
    in_cell: dict[str, list[Event]] = defaultdict(list)
    for e in street:
        own[e.h3] += contribution(e)
        in_cell[e.h3].append(e)

    def ring(c: str) -> list[str]:
        return list(h3.grid_ring(c, 1))

    local = crime.local_values(own, ring)
    nearby = {c: in_cell[c] + [e for n in ring(c) for e in in_cell.get(n, [])] for c in cells}

    by_hood: dict[int, list[float]] = defaultdict(list)
    for c, hood in cells.items():
        by_hood[hood].append(local[c])
    hood_avg = {hood: sum(v) / len(v) for hood, v in by_hood.items()}

    smoothed = {c: crime.lean_toward_neighbourhood(local[c], len(nearby[c]), hood_avg[cells[c]]) for c in cells}

    counts_by_cell: dict[str, list[tuple[float, date]]] = defaultdict(list)
    for cell, rate, day in traffic or []:
        counts_by_cell[cell].append((rate, day))
    rates = [rate for _, rate, _ in traffic or []]
    city_median = median(rates) if rates else crime.FOOT_TRAFFIC_FLOOR
    busy_from = crime.busy_area_threshold(rates)
    foot = {c: crime.foot_traffic_estimate(c, counts_by_cell, city_median, h3.grid_disk) for c in cells}
    per_person = {c: crime.per_person(smoothed[c], foot[c].per_hour) for c in cells}
    typical = median(per_person.values())  # the typical Toronto block, all day
    scores = {c: crime.relative_score(v, typical) for c, v in per_person.items()}

    # Time of day: each block's incidents by hour (leaning toward the city's pattern), per person out at that hour,
    # compared with the same all-day typical block, so emptier hours score higher where incidents continue.
    weight_of = {e: contribution(e) for e in street}
    city_shares = crime.window_shares([local_hour(e) for e in street], [weight_of[e] for e in street])
    activity = activity or [1.0] * 24
    intensity_by_hour, per_person_by_hour = {}, {}
    for c in cells:
        near = nearby[c]
        shares = crime.window_shares([local_hour(e) for e in near], [weight_of[e] for e in near])
        intensity_by_hour[c] = [crime.intensity(crime.lean_toward_city(shares[h], len(near), city_shares[h]))
                                for h in range(24)]
        for h in range(24):
            per_person_by_hour[(c, h)] = crime.per_person_at_hour(
                smoothed[c], intensity_by_hour[c][h], foot[c].per_hour, activity[h])
    scores_by_hour = {k: crime.relative_score(v, typical) for k, v in per_person_by_hour.items()}
    as_of = newest.astimezone(TORONTO_TZ).date().isoformat()

    out = {}
    for c, hood in cells.items():
        near = nearby[c]
        groups = defaultdict(lambda: [0, 0.0])
        for e in near:
            groups[e.group][0] += 1
            groups[e.group][1] += e.weight
        # Lead with the most frequent offence; the most serious one (if different) comes next.
        by_count = sorted(groups, key=lambda g: (-groups[g][0], -groups[g][1]))
        shown = by_count[:1]
        if groups:
            heaviest = max(groups, key=lambda g: groups[g][1])
            shown += [heaviest] if heaviest not in shown else by_count[1:2]
        incident_reasons = [
            Reason("crime", f"{counted(groups[g][0], g)} within about 250 m in the last {crime.HOMICIDE_YEARS} years (each counted at one third)"
                   if g == "homicides" else
                   f"{counted(groups[g][0], g)} within about 250 m in the last 12 months (outdoors, transit or businesses)",
                   source_key=(src := GROUP_SOURCE.get(g, "tps_mci")), value=groups[g][0], as_of=as_of,
                   collected_at=used.get(src, {}).get("collected_at")).to_dict()
            for g in shown
        ]
        busy = foot[c].per_hour >= busy_from and not foot[c].estimated
        # Order matters: the API shows the first two crime reasons.
        reasons = incident_reasons[:1] + [typical_block_reason(
            crime.times_typical(per_person[c], typical), foot[c], busy, city_median, as_of,
            used.get("tps_mci", {}).get("collected_at"))]
        if len(near) < crime.MIN_INCIDENTS:
            reasons.append(Reason("crime", f"Few street incidents recorded nearby, so this score leans on the "
                                  f"{hood_names[hood]} average", source_key="tps_mci", value=len(near), as_of=as_of,
                                  collected_at=used.get("tps_mci", {}).get("collected_at")).to_dict())
        reasons += incident_reasons[1:]
        out[c] = {"incident_count": len(near), "own_value": own[c], "local_value": local[c],
                  "smoothed_value": smoothed[c], "crime_score": scores[c], "reasons": reasons,
                  "foot_traffic": foot[c], "per_person_value": per_person[c],
                  "vs_surroundings": crime.surroundings_ratio(c, per_person, h3.grid_disk), "busy_area": busy,
                  "crime_score_by_hour": [scores_by_hour[(c, h)] for h in range(24)],
                  "intensity_by_hour": [round(x, 3) for x in intensity_by_hour[c]]}
    return out


async def build(conn: asyncpg.Connection) -> dict:
    edition = get_settings().csi_edition
    weights = {r["offence_key"]: float(r["weight"]) for r in
               await conn.fetch("SELECT offence_key, weight FROM csi_weights WHERE edition = $1", edition)}
    events = await load_events(conn, edition)
    used = await source_dates(conn, ["statcan_csi", "tps_ncr", "tps_mci", "tps_shootings", "tps_homicides", "toronto_tmc",
                                     "activity_profile"])
    used_json = json.dumps(used)

    hoods = [dict(r) | {"counts": json.loads(r["counts"])} for r in
             await conn.fetch("SELECT id, external_id, name, population, counts FROM neighbourhoods")]
    ncr_extra = {m.ucr_code: (m.csi_offence_key, m.group_label)
                 for m in load_offence_map().rows() if m.source_key == "tps_ncr"}
    hood_rows = neighbourhood_scores(events, hoods, weights, ncr_extra, used)
    add_trends(hood_rows, [CrimeYear(str(r["neighbourhood_id"]), r["year"], r["offence"], r["count"], r["rate_per_100k"])
                           for r in await conn.fetch("SELECT neighbourhood_id, year, offence, count, rate_per_100k"
                                                     " FROM neighbourhood_crime_years")], used)
    census = {r["external_id"]: r for r in await conn.fetch(
        "SELECT external_id, median_household_income, low_income_pct, census_year FROM neighbourhood_census")}
    # Fairness uses the underlying rates: the same order as the scores, unaffected by capping at 0 and 100.
    paired = [(hood_rows[h["id"]]["weighted_rate"], census[h["external_id"]]) for h in hoods if h["external_id"] in census]

    cells = {r["h3"]: r["neighbourhood_id"] for r in await conn.fetch("SELECT h3::text AS h3, neighbourhood_id FROM cells")}
    traffic = [(r["h3"], float(r["per_hour"]), r["count_date"]) for r in await conn.fetch(
        "SELECT h3::text AS h3, pedestrians / hours AS per_hour, count_date FROM foot_traffic_counts"
        " WHERE count_date >= $1", crime.FOOT_TRAFFIC_SINCE)]
    activity = [float(r["factor_used"]) for r in await conn.fetch("SELECT factor_used FROM activity_by_hour ORDER BY hour")]
    cell_rows = cell_scores(events, cells, {h["id"]: h["name"] for h in hoods}, used, traffic,
                            activity if len(activity) == 24 else None)

    async with conn.transaction():
        if paired:
            scores = [s for s, _ in paired]
            rho_income = fairness.spearman(scores, [float(c["median_household_income"]) for _, c in paired])
            rho_low = fairness.spearman(scores, [float(c["low_income_pct"]) for _, c in paired])
            await conn.execute(
                "INSERT INTO fairness_checks (rho_income, rho_low_income, n, label, census_year) VALUES ($1, $2, $3, $4, $5)",
                rho_income, rho_low, len(paired), fairness.label(rho_income, rho_low), paired[0][1]["census_year"])
        await conn.executemany(
            "INSERT INTO neighbourhood_scores (neighbourhood_id, weighted_rate, crime_score, reasons, details, sources_used, computed_at)"
            " VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, now()) ON CONFLICT (neighbourhood_id) DO UPDATE SET"
            " weighted_rate = $2, crime_score = $3, reasons = $4::jsonb, details = $5::jsonb, sources_used = $6::jsonb, computed_at = now()",
            [(hid, r["weighted_rate"], r["crime_score"], json.dumps(r["reasons"]), json.dumps(r["details"]), used_json)
             for hid, r in hood_rows.items()],
        )
        await conn.execute(
            "CREATE TEMP TABLE cell_scores_load (h3 text, incident_count int, own_value float8, local_value float8,"
            " smoothed_value float8, crime_score int, reasons jsonb, foot_traffic_per_hour float8,"
            " foot_traffic_counts_used int, foot_traffic_first_date date, foot_traffic_last_date date,"
            " per_person_value float8, vs_surroundings float8, busy_area bool, crime_score_by_hour smallint[],"
            " intensity_by_hour real[]) ON COMMIT DROP"
        )
        await conn.copy_records_to_table("cell_scores_load", records=[
            (c, r["incident_count"], r["own_value"], r["local_value"], r["smoothed_value"], r["crime_score"],
             json.dumps(r["reasons"]), r["foot_traffic"].per_hour, r["foot_traffic"].counts_used,
             r["foot_traffic"].first_date, r["foot_traffic"].last_date, r["per_person_value"], r["vs_surroundings"],
             r["busy_area"], r["crime_score_by_hour"], r["intensity_by_hour"]) for c, r in cell_rows.items()])
        columns = ["incident_count", "own_value", "local_value", "smoothed_value", "crime_score", "reasons",
                   "foot_traffic_per_hour", "foot_traffic_counts_used", "foot_traffic_first_date",
                   "foot_traffic_last_date", "per_person_value", "vs_surroundings", "busy_area",
                   "crime_score_by_hour", "intensity_by_hour"]
        await conn.execute(
            f"INSERT INTO cell_scores (h3, {', '.join(columns)}, sources_used, computed_at)"
            f" SELECT h3::h3index, {', '.join(columns)}, $1::jsonb, now() FROM cell_scores_load"
            f" ON CONFLICT (h3) DO UPDATE SET {', '.join(f'{c} = EXCLUDED.{c}' for c in columns)},"
            " sources_used = EXCLUDED.sources_used, computed_at = now()",
            used_json,
        )
    return {"events": len(events), "neighbourhoods": len(hood_rows), "cells": len(cell_rows)}
