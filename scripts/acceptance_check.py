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

        r, dt = timed(c, "/api/v1/route-risks", **{"from": "Union Station, Toronto", "to": "Kensington Market, Toronto"})
        d = r.json()["data"]
        check("13", r.status_code == 200 and dt < 3 and d["geometry"]["type"] == "LineString" and len(d["riskiest_segments"]) <= 3,
              f"Union Station -> Kensington: {d['distance_m']} m, score {d['score']} {d['band']}, "
              f"{len(d['riskiest_segments'])} stand-out stretch(es), {dt:.2f}s (first call in this run)")

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
