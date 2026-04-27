from __future__ import annotations

import asyncio

import pytest

from app.core.security import auth_cache as auth_cache_module
from app.core.security.auth_cache import AuthCache


class _FakeRedis:
    def __init__(
        self,
        store: dict[str, str],
        close_counter: list[int],
        *,
        label: str,
    ) -> None:
        self._store = store
        self._close_counter = close_counter
        self.label = label

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        _ = ex
        self._store[key] = value

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._store:
                deleted += 1
                del self._store[key]
        return deleted

    async def scan_iter(self, match: str):
        prefix = match[:-1] if match.endswith("*") else match
        for key in list(self._store.keys()):
            if key.startswith(prefix):
                yield key

    async def aclose(self) -> None:
        self._close_counter[0] += 1


@pytest.mark.asyncio
async def test_auth_cache_reuses_redis_client_within_same_loop() -> None:
    store: dict[str, str] = {}
    close_counter = [0]
    created_clients: list[_FakeRedis] = []

    def _factory(*_: object, **__: object) -> _FakeRedis:
        client = _FakeRedis(
            store,
            close_counter,
            label=f"client-{len(created_clients) + 1}",
        )
        created_clients.append(client)
        return client

    cache = AuthCache("redis://cache.test/0", redis_factory=_factory)

    await cache.set_profile_snapshot(
        "tenant-1",
        "user-1",
        {"tenant_id": "tenant-1", "user_id": "user-1"},
        ttl_seconds=60,
    )
    snapshot = await cache.get_profile_snapshot("tenant-1", "user-1")
    await cache.invalidate_profile_snapshot("tenant-1", "user-1")

    assert snapshot == {"tenant_id": "tenant-1", "user_id": "user-1"}
    assert len(created_clients) == 1
    assert close_counter[0] == 0


@pytest.mark.asyncio
async def test_auth_cache_keeps_clients_separate_per_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, str] = {}
    close_counter = [0]
    created_clients: list[_FakeRedis] = []

    def _factory(*_: object, **__: object) -> _FakeRedis:
        client = _FakeRedis(
            store,
            close_counter,
            label=f"client-{len(created_clients) + 1}",
        )
        created_clients.append(client)
        return client

    cache = AuthCache("redis://cache.test/0", redis_factory=_factory)
    loop_a = object()
    loop_b = object()
    current_loop = {"value": loop_a}

    monkeypatch.setattr(
        auth_cache_module.asyncio,
        "get_running_loop",
        lambda: current_loop["value"],
    )

    await cache.set_profile_snapshot(
        "tenant-1",
        "user-1",
        {"tenant_id": "tenant-1", "user_id": "user-1"},
        ttl_seconds=60,
    )
    current_loop["value"] = loop_b
    await cache.get_profile_snapshot("tenant-1", "user-1")

    assert len(created_clients) == 2
    assert created_clients[0] is not created_clients[1]
    assert close_counter[0] == 0


@pytest.mark.asyncio
async def test_auth_cache_aclose_closes_cached_clients_and_clears_cache() -> None:
    store: dict[str, str] = {}
    close_counter = [0]
    created_clients: list[_FakeRedis] = []

    def _factory(*_: object, **__: object) -> _FakeRedis:
        client = _FakeRedis(
            store,
            close_counter,
            label=f"client-{len(created_clients) + 1}",
        )
        created_clients.append(client)
        return client

    cache = AuthCache("redis://cache.test/0", redis_factory=_factory)

    await cache.set_profile_snapshot(
        "tenant-1",
        "user-1",
        {"tenant_id": "tenant-1", "user_id": "user-1"},
        ttl_seconds=60,
    )
    assert len(created_clients) == 1

    await cache.aclose()

    assert close_counter[0] == 1
    assert cache._redis_by_loop == {}


@pytest.mark.asyncio
async def test_auth_cache_failures_do_not_break_request_flows(caplog: pytest.LogCaptureFixture) -> None:
    class _FailingRedis:
        async def get(self, key: str) -> None:
            _ = key
            raise RuntimeError("Task got Future attached to a different loop")

        async def aclose(self) -> None:
            return None

    def _factory(*_: object, **__: object) -> _FailingRedis:
        return _FailingRedis()

    cache = AuthCache("redis://cache.test/0", redis_factory=_factory)

    with caplog.at_level("WARNING", logger="supacrm.performance"):
        snapshot = await cache.get_profile_snapshot("tenant-1", "user-1")
        await cache.invalidate_profile_snapshot("tenant-1", "user-1")

    assert snapshot is None
    assert "auth profile cache lookup failed" in caplog.text
    assert cache._redis_disabled is True
