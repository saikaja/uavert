"""Create (or give a new password to) the website's read-only database user, `uavert_web` (01-03-security.md).

Connects as the owner given by an environment variable, creates the role with plain SQL (so it gets no
neon_superuser rights), applies the grants from db/migrations/011_web_role.sql, and writes the website's
connection string to a file or to a key in .env. The password is never printed.

Usage:
    python scripts/create_web_role.py --owner-env DATABASE_URL --out C:\\Users\\saika\\uavert-web-database-url.txt
    python scripts/create_web_role.py --owner-env TEST_DATABASE_URL --env-key TEST_WEB_DATABASE_URL
"""

import argparse
import asyncio
import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
ROLE = "uavert_web"
GRANTS = ROOT / "db" / "migrations" / "011_web_role.sql"


def owner_url(env_key: str) -> str:
    """The owner's URL from the environment, or else from .env."""
    if os.environ.get(env_key):
        return os.environ[env_key]
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{env_key}="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{env_key} is not set in the environment or .env")


def with_user(url: str, user: str, password: str) -> str:
    parts = urlsplit(url)
    host = parts.netloc.rsplit("@", 1)[1]
    return urlunsplit(parts._replace(netloc=f"{user}:{quote(password, safe='')}@{host}"))


async def main(args) -> int:
    url = owner_url(args.owner_env)
    password = secrets.token_urlsafe(24)
    conn = await asyncpg.connect(url)
    try:
        exists = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)", ROLE)
        # Role names and passwords can't be query parameters; the password is URL-safe base64 (no quotes).
        verb = "ALTER" if exists else "CREATE"
        await conn.execute(f"{verb} ROLE {ROLE} WITH LOGIN PASSWORD '{password}'")
        await conn.execute(GRANTS.read_text(encoding="utf-8"))
        superuser = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_auth_members m JOIN pg_roles g ON g.oid = m.roleid"
            " JOIN pg_roles u ON u.oid = m.member WHERE u.rolname = $1 AND g.rolname = 'neon_superuser')", ROLE)
    finally:
        await conn.close()
    if superuser:
        sys.exit(f"{ROLE} is a member of neon_superuser; it must not be. Stopping.")
    web_url = with_user(url, ROLE, password)
    check = await asyncpg.connect(web_url)
    try:
        who = await check.fetchval("SELECT current_user")
    finally:
        await check.close()
    if args.out:
        Path(args.out).write_text(web_url + "\n", encoding="utf-8")
        where = args.out
    else:
        env = ROOT / ".env"
        text = env.read_text(encoding="utf-8")
        line = f"{args.env_key}={web_url}"
        text = (re.sub(rf"^{args.env_key}=.*$", lambda _: line, text, flags=re.M) if re.search(rf"^{args.env_key}=", text, re.M)
                else text.rstrip("\n") + f"\n# The website's read-only user on the same branch (01-03-security.md).\n{line}\n")
        env.write_text(text, encoding="utf-8")
        where = f".env ({args.env_key})"
    print(f"{'New password for' if exists else 'Created'} {ROLE}; connected as {who}; grants applied; "
          f"connection string written to {where} (password not shown).")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--owner-env", required=True, help="environment or .env key holding the owner's connection string")
    dest = p.add_mutually_exclusive_group(required=True)
    dest.add_argument("--out", help="file to write the website's connection string to")
    dest.add_argument("--env-key", help="key in .env to write the website's connection string to")
    sys.exit(asyncio.run(main(p.parse_args())))
