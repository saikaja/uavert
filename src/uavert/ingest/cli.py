"""The `uavert` command line: migrate, ingest, build-scores, serve."""

import argparse
import asyncio
import sys

from uavert import db
from uavert.ingest import crime, live, news, reference, traffic
from uavert.ingest.runs import ensure_reference_rows
from uavert.sources.http import make_client

# Each ingest target runs its steps in order; a failed step is reported and the rest still run.
TARGETS = {
    "reference": ["reference"],
    "crime": ["crime"],
    "traffic": ["traffic"],
    "aqhi": ["aqhi"],
    "alerts": ["alerts"],
    "news": ["news_cbc", "news_gdelt"],
    "live": ["aqhi", "alerts", "news_cbc", "news_gdelt"],
    "all": ["reference", "crime", "traffic", "aqhi", "alerts", "news_cbc", "news_gdelt"],
}


async def _migrate() -> int:
    conn = await db.connect()
    try:
        applied = await db.migrate(conn)
    finally:
        await conn.close()
    print("Applied: " + ", ".join(applied) if applied else "Database is up to date.")
    return 0


async def _ingest(target: str) -> int:
    steps = {"reference": reference.run, "crime": crime.run, "traffic": traffic.run, "aqhi": live.run_aqhi, "alerts": live.run_alerts,
             "news_cbc": news.run_cbc, "news_gdelt": news.run_gdelt}
    conn = await db.connect()
    failures = []
    try:
        region_id = await ensure_reference_rows(conn)
        async with make_client() as client:
            for name in TARGETS[target]:
                print(f"Ingesting {name} ...", flush=True)
                try:
                    await steps[name](conn, client, region_id)
                    print(f"  {name}: ok")
                except Exception as e:  # report and continue with the next source
                    failures.append(name)
                    print(f"  {name}: FAILED - {type(e).__name__}: {e}")
    finally:
        await conn.close()
    if failures:
        print(f"{len(failures)} step(s) failed: {', '.join(failures)}. Previously stored data was kept.")
        return 1
    return 0


async def _build_scores() -> int:
    from uavert.scoring.build import build

    conn = await db.connect()
    try:
        result = await build(conn)
    finally:
        await conn.close()
    print(f"Scored {result['neighbourhoods']} neighbourhoods and {result['cells']} street cells "
          f"from {result['events']:,} distinct crime events.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uavert")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    ingest = sub.add_parser("ingest", help="collect data from outside sources")
    ingest.add_argument("target", choices=sorted(TARGETS))
    sub.add_parser("build-scores", help="compute and store crime scores")
    serve = sub.add_parser("serve", help="run the API and web map")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        return asyncio.run(_migrate())
    if args.command == "ingest":
        return asyncio.run(_ingest(args.target))
    if args.command == "build-scores":
        return asyncio.run(_build_scores())
    if args.command == "serve":
        import uvicorn

        uvicorn.run("uavert.api.app:app", port=args.port, reload=args.reload)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
