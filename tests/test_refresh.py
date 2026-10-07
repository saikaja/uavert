"""Criterion 32: the server's background refresh records failures and keeps going."""

import pytest

from uavert.api.app import refresh_once
from uavert.config import Settings
from uavert.ingest import steps


@pytest.mark.db
async def test_one_refresh_cycle_with_a_failing_source(test_pool, monkeypatch):
    ran = []

    def fake(name, fail=False):
        async def step(conn, client, region_id):
            ran.append(name)
            if fail:
                raise RuntimeError(f"{name} is down")
        return step

    monkeypatch.setattr(steps, "STEPS", {n: fake(n, fail=(n == "alerts")) for n in steps.LIVE})
    failed = await refresh_once(test_pool)
    assert failed == ["alerts"]
    assert ran == steps.LIVE  # the sources after the failing one still ran


async def test_refresh_never_raises_even_if_the_database_is_unreachable():
    class BrokenPool:
        def acquire(self):
            raise ConnectionError("database down")

    assert await refresh_once(BrokenPool()) == steps.LIVE


def test_refresh_is_off_unless_asked_for(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    monkeypatch.delenv("UAVERT_REFRESH_MINUTES", raising=False)
    assert Settings(_env_file=None).refresh_minutes == 0
    monkeypatch.setenv("UAVERT_REFRESH_MINUTES", "30")
    assert Settings(_env_file=None).refresh_minutes == 30
