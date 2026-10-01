"""Warm up a running server before a demo: wakes the Neon database and fills the address and
route caches, so the first live lookups are fast.

Usage: python scripts/warm_demo.py [base_url]   (default http://localhost:8000)
"""

import sys
import time

import httpx

ADDRESSES = ["100 Queen St W, Toronto", "Union Station, Toronto", "Kensington Market, Toronto",
             "Yonge-Dundas Square, Toronto", "Jane and Finch, Toronto"]
ROUTES = [("Union Station, Toronto", "Kensington Market, Toronto"),
          ("100 Queen St W, Toronto", "Yonge-Dundas Square, Toronto")]


def main(base: str) -> int:
    failures = 0
    with httpx.Client(base_url=base, timeout=60) as c:
        checks = [("/api/v1/health", {})] + [("/api/v1/risk-scores", {"address": a}) for a in ADDRESSES] \
            + [("/api/v1/route-risks", {"from": f, "to": t}) for f, t in ROUTES] + [("/api/v1/neighbourhoods", {})]
        for path, params in checks:
            t = time.perf_counter()
            r = c.get(path, params=params)
            ok = r.status_code == 200
            failures += not ok
            what = params.get("address") or (f"{params['from']} -> {params['to']}" if params else path)
            data = r.json().get("data") if ok else None
            if isinstance(data, dict) and "street" in data:
                detail = f"street {data['street']['score']} ({data['street']['band']}), {data['neighbourhood']['name']}"
            elif isinstance(data, dict) and "score" in data:
                detail = f"route {data['score']} ({data['band']}), {data['distance_m']} m"
            else:
                detail = "" if ok else r.text[:120]
            print(f"{'ok ' if ok else 'ERR'} {r.status_code} {(time.perf_counter() - t) * 1000:6.0f} ms  {what}  {detail}")
    print("Ready." if not failures else f"{failures} check(s) failed; see above.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"))
