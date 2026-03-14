import psycopg
import pytest

from bot.config import Config
from bot.db import repository, ssh_tunnel


class _FakeCursor:
    def __init__(self, *, rows=None, error: Exception | None = None):
        self._rows = rows or []
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _sql, _params):
        if self._error is not None:
            raise self._error

    async def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    async def close(self):
        self.closed = True


class _FakeTunnel:
    def __init__(self, local_bind_port: int):
        self.local_bind_port = local_bind_port
        self.active = True
        self.stopped = False

    def is_active(self) -> bool:
        return self.active

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture(autouse=True)
def reset_repository_state():
    repository._conn = None
    repository._conn_db_url = None
    repository._effective_db_url = "postgresql://localhost/test"
    repository._db_url_provider = None
    yield
    repository._conn = None
    repository._conn_db_url = None
    repository._effective_db_url = "postgresql://localhost/test"
    repository._db_url_provider = None


@pytest.mark.asyncio
async def test_query_retries_once_after_connection_error(monkeypatch):
    connections = [
        _FakeConn(_FakeCursor(error=psycopg.OperationalError("boom"))),
        _FakeConn(_FakeCursor(rows=[("ok",)])),
    ]
    get_conn_calls = 0
    reset_calls = 0

    async def fake_get_conn():
        nonlocal get_conn_calls
        conn = connections[get_conn_calls]
        get_conn_calls += 1
        return conn

    async def fake_reset_conn():
        nonlocal reset_calls
        reset_calls += 1

    monkeypatch.setattr(repository, "_get_conn", fake_get_conn)
    monkeypatch.setattr(repository, "_reset_conn", fake_reset_conn)

    rows = await repository._query("select 1", ())

    assert rows == [("ok",)]
    assert get_conn_calls == 2
    assert reset_calls == 1


@pytest.mark.asyncio
async def test_get_conn_reconnects_when_db_url_changes(monkeypatch):
    urls = iter(
        [
            "postgresql://user:pass@127.0.0.1:41001/db",
            "postgresql://user:pass@127.0.0.1:41002/db",
        ]
    )
    first_conn = _FakeConn(_FakeCursor())
    second_conn = _FakeConn(_FakeCursor())
    connect_calls = []

    repository.set_db_url_provider(lambda: next(urls))

    async def fake_connect(*, conninfo, autocommit):
        assert autocommit is True
        connect_calls.append(conninfo)
        return first_conn if len(connect_calls) == 1 else second_conn

    monkeypatch.setattr(repository.psycopg.AsyncConnection, "connect", fake_connect)

    first = await repository._get_conn()
    second = await repository._get_conn()

    assert first is first_conn
    assert second is second_conn
    assert first_conn.closed is True
    assert connect_calls == [
        "postgresql://user:pass@127.0.0.1:41001/db",
        "postgresql://user:pass@127.0.0.1:41002/db",
    ]


def test_tunnel_manager_restarts_with_previous_local_port(monkeypatch):
    cfg = Config(
        db_sync_url="postgresql://user:pass@db.internal:5432/gov",
        ssh_host="bastion.internal",
        ssh_user="cardano",
        ssh_key_path="/tmp/key",
    )
    first_tunnel = _FakeTunnel(local_bind_port=43123)
    second_tunnel = _FakeTunnel(local_bind_port=43123)
    start_calls = []

    def fake_start_tunnel(_cfg, *, local_port=None):
        start_calls.append(local_port)
        return first_tunnel if len(start_calls) == 1 else second_tunnel

    monkeypatch.setattr(ssh_tunnel, "start_tunnel", fake_start_tunnel)

    manager = ssh_tunnel.SshTunnelManager(cfg)

    assert manager.ensure_active() is first_tunnel

    first_tunnel.active = False

    assert manager.ensure_active() is second_tunnel
    assert start_calls == [None, 43123]
    assert first_tunnel.stopped is True
