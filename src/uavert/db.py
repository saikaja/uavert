"""Database connections and the migration runner."""

import asyncpg

from uavert.config import PROJECT_ROOT, get_settings

MIGRATIONS_DIR = PROJECT_ROOT / "db" / "migrations"


async def create_pool(url: str | None = None) -> asyncpg.Pool:
    return await asyncpg.create_pool(url or get_settings().database_url, min_size=1, max_size=get_settings().db_pool_max)


async def connect(url: str | None = None) -> asyncpg.Connection:
    return await asyncpg.connect(url or get_settings().database_url)


async def migrate(conn: asyncpg.Connection) -> list[str]:
    """Apply each `db/migrations/*.sql` file not applied yet, in name order. Returns the names applied."""
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    done = {r["name"] for r in await conn.fetch("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        async with conn.transaction():
            await conn.execute(path.read_text(encoding="utf-8"))
            await conn.execute("INSERT INTO schema_migrations (name) VALUES ($1)", path.name)
        applied.append(path.name)
    return applied
