from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.workers.tasks import marketing as marketing_worker


class _FakeSession:
    pass


class _FakeBeginContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _build_fake_session_factory(session: _FakeSession):
    class _Factory:
        def __call__(self) -> _FakeSessionContext:
            return _FakeSessionContext(session)

    return _Factory()


def test_execute_marketing_campaign_runs_processor_inside_worker_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    session.begin = lambda: _FakeBeginContext(session)
    observed = SimpleNamespace(tenant_id=None, execution_id=None)

    async def _fake_set_tenant_guc(db_session, tenant_id: str) -> None:
        assert db_session is session
        observed.tenant_id = tenant_id

    async def _fake_process(db_session, *, execution_id: str) -> None:
        assert db_session is session
        observed.execution_id = execution_id

    monkeypatch.setattr(marketing_worker, "async_session_factory", _build_fake_session_factory(session))
    monkeypatch.setattr(marketing_worker, "set_tenant_guc", _fake_set_tenant_guc)
    monkeypatch.setattr(marketing_worker, "process_email_campaign_execution", _fake_process)

    marketing_worker.execute_marketing_campaign(execution_id="execution-1", tenant_id="tenant-1")

    assert observed.tenant_id == "tenant-1"
    assert observed.execution_id == "execution-1"


def test_execute_marketing_campaign_marks_execution_failed_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    session.begin = lambda: _FakeBeginContext(session)
    failure_mark = SimpleNamespace(reason=None)

    async def _fake_set_tenant_guc(db_session, tenant_id: str) -> None:
        assert db_session is session
        assert tenant_id == "tenant-1"

    async def _fake_process(db_session, *, execution_id: str) -> None:
        assert db_session is session
        assert execution_id == "execution-1"
        raise RuntimeError("SMTP transport crashed")

    async def _fake_fail(db_session, *, execution_id: str, failure_reason: str) -> None:
        assert db_session is session
        assert execution_id == "execution-1"
        failure_mark.reason = failure_reason

    monkeypatch.setattr(marketing_worker, "async_session_factory", _build_fake_session_factory(session))
    monkeypatch.setattr(marketing_worker, "set_tenant_guc", _fake_set_tenant_guc)
    monkeypatch.setattr(marketing_worker, "process_email_campaign_execution", _fake_process)
    monkeypatch.setattr(marketing_worker, "fail_marketing_campaign_execution", _fake_fail)

    with pytest.raises(RuntimeError, match="SMTP transport crashed"):
        marketing_worker.execute_marketing_campaign(execution_id="execution-1", tenant_id="tenant-1")

    assert failure_mark.reason == "Worker execution failed: SMTP transport crashed"
