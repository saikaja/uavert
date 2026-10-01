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
from uavert.ingest.reference import load_offence_map
from uavert.scoring import crime
from uavert.scoring.combine import Reason
from uavert.scoring.events import count_once

NEIGHBOURHOOD_YEAR = 2025
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
    rows = await conn.fetch(
        "SELECT i.event_id, i.source_key, i.ucr_code, i.ucr_ext, i.csi_offence_key, w.weight, i.premises_type,"
        " i.occurred_at, i.hood_external_id, i.h3::text AS h3"
        " FROM incidents i JOIN csi_weights w ON w.edition = $1 AND w.offence_key = i.csi_offence_key",
        edition,
    )
    events = [
        Event(r["event_id"], r["source_key"], r["csi_offence_key"], float(r["weight"]),
              offence_map.resolve(r["source_key"], r["ucr_code"], r["ucr_ext"]).group_label,
              r["premises_type"], r["occurred_at"], r["hood_external_id"], r["h3"])
        for r in rows
    ]
    return count_once(events, event_id=lambda e: e.event_id, weight=lambda e: e.weight)


def neighbourhood_scores(events: list[Event], hoods: list[dict], weights: dict[str, float], ncr_extra: dict[str, tuple[str, str]], used: dict) -> dict[int, dict]:
    """Calendar-year CSI-weighted rate per 100,000 residents, ranked across the city.

    `hoods`: dicts with id, external_id, population, counts (published counts for the year).
    `ncr_extra`: published count name -> (csi_offence_key, group) for offences the incident data lacks.
    """
    by_hood: dict[str, Counter] = defaultdict(Counter)  # (csi_key, group) -> count
    for e in events:
        if e.hood_external_id and e.occurred_at.astimezone(TORONTO_TZ).year == NEIGHBOURHOOD_YEAR:
            by_hood[e.hood_external_id][(e.csi_offence_key, e.group)] += 1
    for h in hoods:
        for name, key in ncr_extra.items():
            by_hood[h["external_id"]][key] += h["counts"].get(name, 0)

    rates, details = {}, {}
    for h in hoods:
        counts = by_hood[h["external_id"]]
        pop = h["population"] or 0
        per_offence = Counter()
        for (key, _group), c in counts.items():
            per_offence[key] += c
        rates[h["id"]] = crime.weighted_rate(per_offence, weights, pop)
        groups = defaultdict(lambda: {"count": 0, "weighted": 0.0})
        for (key, group), c in counts.items():
            groups[group]["count"] += c
            groups[group]["weighted"] += c * weights[key]
        details[h["id"]] = {g: {"count": v["count"], "rate_per_100k": v["count"] / pop * 100_000 if pop else 0.0,
                                "weighted": v["weighted"]} for g, v in groups.items()}

    medians = {g: median(d.get(g, {"rate_per_100k": 0.0})["rate_per_100k"] for d in details.values())
               for g in {g for d in details.values() for g in d}}
    scores = crime.percentile_scores(rates)
    out = {}
    for h in hoods:
        d = details[h["id"]]
        top = sorted(d.items(), key=lambda kv: -kv[1]["weighted"])[:2]
        reasons = [
            Reason("crime",
                   f"{counted(v['count'], g)} reported in {NEIGHBOURHOOD_YEAR} "
                   f"({v['rate_per_100k']:,.0f} per 100,000 residents; Toronto median {medians[g]:,.0f})",
                   source_key=(src := GROUP_SOURCE.get(g, "tps_mci")), value=v["count"],
                   as_of=str(NEIGHBOURHOOD_YEAR), collected_at=used.get(src, {}).get("collected_at")).to_dict()
            for g, v in top if v["count"]
        ]
        out[h["id"]] = {"weighted_rate": rates[h["id"]], "crime_score": scores[h["id"]], "reasons": reasons,
                        "details": {"year": NEIGHBOURHOOD_YEAR, "groups": d, "toronto_median_rate_per_100k": medians}}
    return out


def foot_traffic_reason(f: crime.FootTraffic, busy: bool, city_median: float, collected_at: str | None) -> dict:
    if f.estimated:
        text = f"No foot-traffic count nearby; using the Toronto median of about {city_median:,.0f} people an hour"
    else:
        years = str(f.first_date.year) if f.first_date.year == f.last_date.year else f"{f.first_date.year}-{f.last_date.year}"
        plural = "s" if f.counts_used != 1 else ""
        counted = f"{f.counts_used} City of Toronto count{plural}, {years}"
        if busy:
            text = f"Busy area: about {f.per_hour:,.0f} people an hour on foot nearby ({counted}); the score allows for crowds"
        else:
            text = f"About {f.per_hour:,.0f} people an hour on foot nearby ({counted}); the score allows for this"
    return Reason("crime", text, "toronto_tmc", value=round(f.per_hour),
                  as_of=f.last_date.isoformat() if f.last_date else None, collected_at=collected_at).to_dict()


def cell_scores(events: list[Event], cells: dict[str, int], hood_names: dict[int, str], used: dict,
                traffic: list[tuple[str, float, date]] | None = None) -> dict[str, dict]:
    """Street score per H3 cell: the last 12 months of street incidents, per person on foot nearby.

    `cells`: h3 -> neighbourhood id for every cell in the grid.
    `traffic`: (h3, pedestrians per hour, count date) for each counted location since FOOT_TRAFFIC_SINCE.
    """
    street = [e for e in events if e.h3 and crime.counts_on_street(e.premises_type)]
    newest = max(e.occurred_at for e in street)
    since = newest - timedelta(days=STREET_WINDOW_DAYS)
    street = [e for e in street if e.occurred_at > since and e.h3 in cells]

    own = dict.fromkeys(cells, 0.0)
    in_cell: dict[str, list[Event]] = defaultdict(list)
    for e in street:
        own[e.h3] += e.weight * crime.recency_weight((newest - e.occurred_at).total_seconds() / 86400)
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
    scores = crime.percentile_scores(per_person)
    as_of = newest.astimezone(TORONTO_TZ).date().isoformat()

    out = {}
    for c, hood in cells.items():
        near = nearby[c]
        groups = defaultdict(lambda: [0, 0.0])
        for e in near:
            groups[e.group][0] += 1
            groups[e.group][1] += e.weight
        incident_reasons = [
            Reason("crime", f"{counted(n, g)} within about 250 m in the last 12 months (outdoors, transit or businesses)",
                   source_key=(src := GROUP_SOURCE.get(g, "tps_mci")), value=n, as_of=as_of,
                   collected_at=used.get(src, {}).get("collected_at")).to_dict()
            for g, (n, _) in sorted(groups.items(), key=lambda kv: -kv[1][1])[:2]
        ]
        busy = foot[c].per_hour >= busy_from and not foot[c].estimated
        # Order matters: the API shows the first two crime reasons.
        reasons = incident_reasons[:1] + [
            foot_traffic_reason(foot[c], busy, city_median, used.get("toronto_tmc", {}).get("collected_at"))]
        if len(near) < crime.MIN_INCIDENTS:
            reasons.append(Reason("crime", f"Few street incidents recorded nearby, so this score leans on the "
                                  f"{hood_names[hood]} average", source_key="tps_mci", value=len(near), as_of=as_of,
                                  collected_at=used.get("tps_mci", {}).get("collected_at")).to_dict())
        reasons += incident_reasons[1:]
        out[c] = {"incident_count": len(near), "own_value": own[c], "local_value": local[c],
                  "smoothed_value": smoothed[c], "crime_score": scores[c], "reasons": reasons,
                  "foot_traffic": foot[c], "per_person_value": per_person[c],
                  "vs_surroundings": crime.surroundings_ratio(c, per_person, h3.grid_disk), "busy_area": busy}
    return out


async def build(conn: asyncpg.Connection) -> dict:
    edition = get_settings().csi_edition
    weights = {r["offence_key"]: float(r["weight"]) for r in
               await conn.fetch("SELECT offence_key, weight FROM csi_weights WHERE edition = $1", edition)}
    events = await load_events(conn, edition)
    used = await source_dates(conn, ["statcan_csi", "tps_ncr", "tps_mci", "tps_shootings", "tps_homicides", "toronto_tmc"])
    used_json = json.dumps(used)

    hoods = [dict(r) | {"counts": json.loads(r["counts"])} for r in
             await conn.fetch("SELECT id, external_id, name, population, counts FROM neighbourhoods")]
    ncr_extra = {m.ucr_code: (m.csi_offence_key, m.group_label)
                 for m in load_offence_map().rows() if m.source_key == "tps_ncr"}
    hood_rows = neighbourhood_scores(events, hoods, weights, ncr_extra, used)

    cells = {r["h3"]: r["neighbourhood_id"] for r in await conn.fetch("SELECT h3::text AS h3, neighbourhood_id FROM cells")}
    traffic = [(r["h3"], float(r["per_hour"]), r["count_date"]) for r in await conn.fetch(
        "SELECT h3::text AS h3, pedestrians / hours AS per_hour, count_date FROM foot_traffic_counts"
        " WHERE count_date >= $1", crime.FOOT_TRAFFIC_SINCE)]
    cell_rows = cell_scores(events, cells, {h["id"]: h["name"] for h in hoods}, used, traffic)

    async with conn.transaction():
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
            " per_person_value float8, vs_surroundings float8, busy_area bool) ON COMMIT DROP"
        )
        await conn.copy_records_to_table("cell_scores_load", records=[
            (c, r["incident_count"], r["own_value"], r["local_value"], r["smoothed_value"], r["crime_score"],
             json.dumps(r["reasons"]), r["foot_traffic"].per_hour, r["foot_traffic"].counts_used,
             r["foot_traffic"].first_date, r["foot_traffic"].last_date, r["per_person_value"], r["vs_surroundings"],
             r["busy_area"]) for c, r in cell_rows.items()])
        columns = ["incident_count", "own_value", "local_value", "smoothed_value", "crime_score", "reasons",
                   "foot_traffic_per_hour", "foot_traffic_counts_used", "foot_traffic_first_date",
                   "foot_traffic_last_date", "per_person_value", "vs_surroundings", "busy_area"]
        await conn.execute(
            f"INSERT INTO cell_scores (h3, {', '.join(columns)}, sources_used, computed_at)"
            f" SELECT h3::h3index, {', '.join(columns)}, $1::jsonb, now() FROM cell_scores_load"
            f" ON CONFLICT (h3) DO UPDATE SET {', '.join(f'{c} = EXCLUDED.{c}' for c in columns)},"
            " sources_used = EXCLUDED.sources_used, computed_at = now()",
            used_json,
        )
    return {"events": len(events), "neighbourhoods": len(hood_rows), "cells": len(cell_rows)}
