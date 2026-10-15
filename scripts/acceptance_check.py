"""Check the acceptance criteria against a running server and the real data, over HTTP.

Usage: python scripts/acceptance_check.py [base_url]   (default http://localhost:8000)
Prints one line per check with PASS/FAIL, the evidence and timings. Exit code 1 if any check fails.
"""

import re
import sys
import time

import httpx

from uavert.ingest.registry import SOURCE_KEYS

results: list[tuple[str, bool, str]] = []


def check(criterion: str, ok: bool, evidence: str) -> None:
    results.append((criterion, ok, evidence))
    print(f"{'PASS' if ok else 'FAIL'}  {criterion:5} {evidence}")


def timed(c: httpx.Client, path: str, **params):
    t = time.perf_counter()
    r = c.get(path, params=params)
    return r, time.perf_counter() - t


def main(base: str) -> int:
    with httpx.Client(base_url=base, timeout=60) as c:
        r, dt = timed(c, "/api/v1/health")
        check("setup", r.status_code == 200, f"health {r.status_code} in {dt:.2f}s (first call wakes the database)")

        sources = {s["key"]: s for s in c.get("/api/v1/sources").json()["data"]}
        check("3", bool(sources["eccc_aqhi"]["collected_at"]) and sources["eccc_alerts"]["last_status"] == "ok",
              f"AQHI data {sources['eccc_aqhi']['as_of']}, collected {sources['eccc_aqhi']['collected_at']}; alerts last_status ok")
        complete = all(s["name"] and s["licence"] and s["attribution"] for s in sources.values())
        check("4", complete and set(sources) == SOURCE_KEYS,
              f"{len(sources)} sources, each with name, licence, attribution; statuses: "
              + ", ".join(f"{k}={s['last_status']}" for k, s in sorted(sources.items())))

        hoods = c.get("/api/v1/neighbourhoods").json()
        feats = hoods["data"]["features"]
        p = feats[0]["properties"]
        check("10", len(feats) == 158 and {"score", "band", "categories"} <= set(p) and feats[0]["geometry"],
              f"{len(feats)} neighbourhoods with score, band, categories, GeoJSON; meta.sources has "
              f"{len(hoods['meta']['sources'])} entries with as_of and collected_at")
        mimico = next(f["properties"] for f in feats if f["properties"]["name"] == "Mimico-Queensway")
        check("odds-r2", mimico["score"] <= 30, f"Mimico-Queensway {mimico['score']} with jail incidents left out (was 40)")
        detail = c.get(f"/api/v1/neighbourhoods/{p['id']}").json()["data"]
        ok = 1 <= len(detail["reasons"]) <= 3 and all(x["source_key"] and "as_of" in x and "collected_at" in x for x in detail["reasons"])
        check("10b", ok, f"{detail['name']}: {len(detail['reasons'])} reasons, e.g. \"{detail['reasons'][0]['text']}\"")

        cells, dt = timed(c, "/api/v1/cells", bbox="-79.40,43.64,-79.37,43.66")
        cp = cells.json()["data"]["features"][0]["properties"]
        check("11", cells.status_code == 200 and {"score", "band", "incident_count", "top_reason", "foot_traffic_per_hour"} <= set(cp),
              f"{len(cells.json()['data']['features'])} cells in {dt:.2f}s, e.g. score {cp['score']}, {cp['incident_count']} incidents")

        r, dt = timed(c, "/api/v1/risk-scores", address="100 Queen St W, Toronto")
        d = r.json()["data"]
        check("12", r.status_code == 200 and dt < 2,
              f"100 Queen St W -> {d['location']['display_name'][:40]}...: street {d['street']['score']} {d['street']['band']}, "
              f"neighbourhood {d['neighbourhood']['name']} {d['neighbourhood']['score']}, {dt:.2f}s (first call in this run)")
        odds = d["neighbourhood"].get("odds") or {}
        levels = odds.get("levels", {})
        check("odds-1", set(levels) == {"high", "medium", "low", "any"} and odds.get("year") == 2025
              and all(l["one_in"] is None or l["one_in"] >= 1 for l in levels.values()),
              f"{d['neighbourhood']['name']}: " + ", ".join(f"{k} 1 in {levels[k]['one_in']}" for k in sorted(levels)))
        toronto = {k: l["toronto_one_in"] for k, l in levels.items()}
        check("odds-3", 50 <= toronto.get("any", 0) <= 100 and toronto.get("high", 0) > toronto.get("medium", 0) > toronto.get("any", 0),
              f"Toronto 2025: " + ", ".join(f"{k} 1 in {v}" for k, v in sorted(toronto.items())))
        check("odds-1b", bool(detail.get("odds", {}).get("levels")), f"/neighbourhoods/{p['id']} has odds")
        trend = d["neighbourhood"].get("trend") or {}
        w10 = trend.get("windows", {}).get("10", {})
        check("trends-2", [x["year"] for x in trend.get("series", {}).get("violent", [])] == list(range(2016, 2026))
              and trend.get("windows", {}).get("5", {}).get("first_year") == 2021 and len(w10.get("offences", {})) == 9,
              f"{d['neighbourhood']['name']}: violent {w10.get('groups', {}).get('violent')}, "
              f"property {w10.get('groups', {}).get('property')}")
        tg = trend.get("toronto", {}).get("windows", {}).get("10", {}).get("groups", {})
        check("trends-3", abs(tg.get("violent", {}).get("change_pct", 99) - 10) <= 1
              and abs(tg.get("property", {}).get("change_pct", 99) - 5) <= 1,
              f"Toronto 2016-2025: violent {tg.get('violent', {}).get('change_pct')}%, property {tg.get('property', {}).get('change_pct')}%")
        check("trends-2b", bool(detail.get("trend", {}).get("windows")), f"/neighbourhoods/{p['id']} has a trend")

        r, dt = timed(c, "/api/v1/route-risks", **{"from": "Union Station, Toronto", "to": "Kensington Market, Toronto"})
        d = r.json()["data"]
        check("13", r.status_code == 200 and dt < 3 and d["geometry"]["type"] == "LineString" and len(d["riskiest_segments"]) <= 3,
              f"Union Station -> Kensington: {d['distance_m']} m, score {d['score']} {d['band']}, "
              f"{len(d['riskiest_segments'])} stand-out stretch(es), {dt:.2f}s (first call in this run)")
        t = d.get("typical") or {}
        check("tidy-54", t.get("score") is not None and t["score"] == d.get("typical_score") and t["score"] <= d["score"]
              and set(t) >= {"band", "categories", "reasons"},
              f"Union Station -> Kensington: typical block {t.get('score')} {t.get('band')} (headline), worst block {d['score']} {d['band']}")

        for label, params, status, code in [
            ("outside", {"address": "100 City Centre Dr, Mississauga"}, 422, "outside_coverage"),
            ("not found", {"address": "zzqqxx nowhere 12345"}, 404, "address_not_found"),
        ]:
            r = c.get("/api/v1/risk-scores", params=params)
            check("14", r.status_code == status and r.json()["error"]["code"] == code,
                  f"{label}: {r.status_code} {r.json()['error']['code']}: {r.json()['error']['message'][:70]}")
        r = c.get("/api/v1/route-risks", params={"from": "Union Station, Toronto", "to": "Scarborough Town Centre, Toronto"})
        check("14", r.status_code == 422 and r.json()["error"]["code"] == "route_too_long", f"too far: {r.status_code} {r.json()['error']['message']}")

        news = c.get("/api/v1/news-events", params={"since_hours": 48}).json()["data"]
        check("15", sources["news_cbc"]["last_status"] == "ok",
              f"CBC collected {sources['news_cbc']['collected_at']}; {len(news)} labelled report(s) in 48 h; "
              f"GDELT last_status={sources['news_gdelt']['last_status']}")

        texts = []
        for path in ["/api/v1/neighbourhoods", f"/api/v1/neighbourhoods/{p['id']}", "/api/v1/cells?bbox=-79.40,43.64,-79.37,43.66",
                     "/api/v1/scoring-rules", "/api/v1/risk-scores?address=100 Queen St W, Toronto&hour=2"]:
            texts.append(c.get(path).text)
        labelled_safe = any(re.search(r'"(band|label)"\s*:\s*"[^"]*safe', t, re.I) for t in texts)
        check("9", not labelled_safe, "no band or label containing 'safe' in 5 live responses")

        r = c.get("/api/v1/risk-scores", params={"address": "100 Queen St W, Toronto"})
        allday = r.json()["data"]
        check("21", allday["time"]["label"] == "All day", "no hour -> time.label 'All day'")
        r = c.get("/api/v1/risk-scores", params={"address": "100 Queen St W, Toronto", "hour": 24})
        check("21", r.status_code == 422, f"hour=24 -> {r.status_code} {r.json()['error']['code']}")
        at = {h: c.get("/api/v1/risk-scores", params={"address": "100 Queen St W, Toronto", "hour": h}).json()["data"] for h in (2, 14)}
        check("25", at[2]["street"]["score"] > at[14]["street"]["score"],
              f"City Hall street score 2 am {at[2]['street']['score']} > 2 pm {at[14]['street']['score']}")
        reason = at[2]["street"]["reasons"][0]
        check("26", reason["text"].startswith("At 2 am:") and "estimated from Bike Share" in reason["text"],
              f"\"{reason['text']}\"")
        check("27", bool(sources["activity_profile"]["as_of"] and sources["activity_profile"]["collected_at"]),
              f"activity_profile as_of {sources['activity_profile']['as_of']}, collected {sources['activity_profile']['collected_at']}")

        # Time of day on the neighbourhood map (01-03-time-map.md)
        bodies = {h: c.get("/api/v1/neighbourhoods", params={} if h is None else {"hour": h}).json()["data"]
                  for h in (None, 2, 14)}
        hoods_at = {h: {f["properties"]["name"]: f["properties"] for f in b["features"]} for h, b in bodies.items()}
        r = c.get("/api/v1/neighbourhoods", params={"hour": 24})
        check("29", r.status_code == 422 and bodies[None]["time"]["label"] == "All day" and bodies[2]["time"]["label"] == "2 am",
              f"no hour -> 'All day'; hour=2 -> '2 am'; hour=24 -> {r.status_code}")
        crime_by_hour = lambda name: [hoods_at[h][name]["categories"]["crime"] for h in (None, 2, 14)]
        yb, gw = crime_by_hour("Yonge-Bay Corridor"), crime_by_hour("Guildwood")
        check("31", yb[1] > yb[2] and max(gw) - min(gw) <= 10,
              f"crime all day / 2 am / 2 pm: Yonge-Bay Corridor {yb}, Guildwood {gw}")
        kc = hoods_at[None]["Kensington-Chinatown"]["id"]
        kd = c.get(f"/api/v1/neighbourhoods/{kc}", params={"hour": 2}).json()["data"]
        kr = next((x for x in kd["reasons"] if x["category"] == "crime"), {})
        check("32", kd["time"]["label"] == "2 am" and kr.get("text", "").startswith("At 2 am: street blocks here")
              and kr.get("source_key") == "activity_profile", f"Kensington-Chinatown {kd['score']} at 2 am: \"{kr.get('text')}\"")
        page, js = c.get("/").text, c.get("/app.js").text
        check("34", "dest-form" not in page and "Where I'm going" not in page and "route-form" in page,
              "page has Where I'm walking and no Where I'm going")
        check("35", all(colour in js for colour in ("#2e9e57", "#f2c230", "#e8792b", "#c62828")),
              "app.js bands: green #2e9e57, yellow #f2c230, orange #e8792b, red #c62828")

        # News by type, trending and police patterns (01-03-news.md); information only
        typed = c.get("/api/v1/news-events", params={"window": "by_type", "limit": 100}).json()["data"]
        windows = {n["category"]: n["window_days"] for n in typed}
        check("news-37", all(windows.get(k, v) == v for k, v in {"protest": 2, "violent_incident": 7, "property_crime": 60}.items()),
              f"{len(typed)} stories by type: " + ", ".join(f"{k} {sum(n['category'] == k for n in typed)}" for k in
                                                          ("protest", "violent_incident", "property_crime")))
        feeds = {k: sources.get(k, {}) for k in ("news_citynews", "news_global", "news_star")}
        check("news-38", all(f.get("collected_at") for f in feeds.values()),
              "; ".join(f"{k}: collected {f.get('collected_at')}, last {f.get('last_status')}" for k, f in feeds.items()))
        trend = c.get("/api/v1/news-trending")
        groups_ = trend.json()["data"]
        check("news-39", trend.status_code == 200 and all(g["story_count"] >= 3 and g["outlet_count"] >= 2 for g in groups_),
              f"{len(groups_)} trending: " + "; ".join(f"{g['story_count']} stories/{g['outlet_count']} outlets: "
                                                      f"{g['headline'][:50]}" for g in groups_[:3]))
        pats = c.get("/api/v1/crime-patterns").json()["data"]
        check("news-40", all(p["recent"] >= 5 and p["times_usual"] >= 2 and p["data_as_of"] for p in pats),
              f"{len(pats)} pattern(s): " + "; ".join(f"{p['neighbourhood']} {p['recent']} {p['offence_label']} "
                                                     f"(usual {p['usual_per_30_days']})" for p in pats[:4]))
        check("news-42", "News and patterns" in page and "crime-patterns" in js and "news-trending" in js,
              "page has the News and patterns section")

        # Edge caching (01-03-security.md): successful answers carry s-maxage; behind Vercel the repeat is a cache hit
        first = c.get("/api/v1/scoring-rules")
        again = c.get("/api/v1/scoring-rules")
        # Vercel's CDN consumes s-maxage and passes on only "public, max-age=0"; behind it, X-Vercel-Cache shows caching.
        health = c.get("/api/v1/health").headers
        check("sec-43", ("s-maxage=300" in first.headers.get("cache-control", "") or "x-vercel-cache" in first.headers)
              and "s-maxage" not in health.get("cache-control", "") and health.get("x-vercel-cache") != "HIT",
              f"Cache-Control: {first.headers.get('cache-control')}; X-Vercel-Cache: {first.headers.get('x-vercel-cache')}; "
              f"health X-Vercel-Cache: {health.get('x-vercel-cache')}")
        edge = again.headers.get("x-vercel-cache")
        check("sec-44", edge is None or edge in ("HIT", "STALE"),
              f"repeat request: X-Vercel-Cache {edge}" if edge else "no CDN in front (local run)")

        r, dt = timed(c, "/api/v1/route-risks", **{"from": "Union Station, Toronto", "to": "125 Blue Jays Way, Toronto"})
        w = r.json()["data"]
        check("41", r.status_code == 200 and 45 <= w["score"] <= 60 and w["band"] != "high",
              f"Union Station -> 125 Blue Jays Way: score {w['score']} {w['band']} (was 80-84 high), "
              f"typical {w.get('typical_score')} {w.get('typical_band')}, {dt:.2f}s")
        check("44", w.get("typical_score") is not None and w.get("typical_band"), "walk has typical_score and typical_band")
        check("51", "crowds" in w["categories"], f"categories: {sorted(w['categories'])}")

        rules = c.get("/api/v1/scoring-rules").json()["data"]
        check("40", rules["parameters"].get("points_per_doubling") == 20,
              f"scale: {rules['parameters'].get('score_scale')}; alert colours {rules['parameters'].get('alert_colour_scores')}")
        check("2", rules["csi_edition"] == "2009" and len(rules["csi_weights"]) == 26 and len(rules["offence_map"]) == 24,
              f"CSI edition {rules['csi_edition']}, {len(rules['csi_weights'])} weights, {len(rules['offence_map'])} mappings")

        for path in ["/", "/rules.html", "/api/docs"]:
            r = c.get(path)
            check("19", r.status_code == 200, f"{path} -> {r.status_code}, {len(r.content):,} bytes")

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"))
