"""The `uavert` command line: migrate, ingest, build-scores, serve."""

import argparse
import asyncio
import sys

import logging
import os

from uavert import db
from uavert.ingest.steps import TARGETS, run_steps


async def _migrate() -> int:
    conn = await db.connect()
    try:
        applied = await db.migrate(conn)
    finally:
        await conn.close()
    print("Applied: " + ", ".join(applied) if applied else "Database is up to date.")
    return 0


async def _ingest(target: str) -> int:
    conn = await db.connect()
    try:
        failures = await run_steps(conn, TARGETS[target], report=lambda m: print(m, flush=True))
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
    serve.add_argument("--refresh-minutes", type=int, default=30,
                       help="refresh air quality, alerts and news this often while serving (0 = off)")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        return asyncio.run(_migrate())
    if args.command == "ingest":
        return asyncio.run(_ingest(args.target))
    if args.command == "build-scores":
        return asyncio.run(_build_scores())
    if args.command == "serve":
        import uvicorn

        os.environ.setdefault("UAVERT_REFRESH_MINUTES", str(args.refresh_minutes))
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s: %(message)s")
        uvicorn.run("uavert.api.app:app", port=args.port, reload=args.reload)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
