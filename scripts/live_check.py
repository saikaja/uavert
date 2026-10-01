"""Call the API in-process against the real database and live outside services; print status and timing."""

import asyncio
import json
import sys
import time

import httpx

from uavert import db
from uavert.api.app import app


async def main(paths: list[str]) -> None:
    app.state.pool = await db.create_pool()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local", timeout=60) as c:
            for path in paths:
                t = time.perf_counter()
                r = await c.get(path)
                print(f"{path}\n  -> {r.status_code} in {(time.perf_counter() - t) * 1000:.0f} ms")
                print("  " + json.dumps(r.json().get("data", r.json()), default=str)[:900])
    finally:
        await app.state.pool.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
