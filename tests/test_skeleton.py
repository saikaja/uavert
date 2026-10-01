import pytest

from uavert import db
from uavert.config import Settings


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/d")
    monkeypatch.setenv("CSI_EDITION", "2018")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql://u:p@h/d"
    assert s.csi_edition == "2018"


@pytest.mark.db
async def test_migrate_twice_changes_nothing(test_db_url):
    conn = await db.connect(test_db_url)
    try:
        assert await db.migrate(conn) == []
    finally:
        await conn.close()


@pytest.mark.db
async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"data": {"status": "ok", "database": "ok"}}
