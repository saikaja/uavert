"""The `uavert` command line: migrate, ingest, build-scores, serve."""

import argparse
import asyncio
import sys

from uavert import db


async def _migrate() -> int:
    conn = await db.connect()
    try:
        applied = await db.migrate(conn)
    finally:
        await conn.close()
    print("Applied: " + ", ".join(applied) if applied else "Database is up to date.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uavert")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply database migrations")
    serve = sub.add_parser("serve", help="run the API and web map")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        return asyncio.run(_migrate())
    if args.command == "serve":
        import uvicorn

        uvicorn.run("uavert.api.app:app", port=args.port, reload=args.reload)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
