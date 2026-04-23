from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from app.auth.service import UserProvisionResult
from app.commercial import deps as commercial_deps
from app.commercial import service as commercial_service
from app.commercial.providers.base import CommercialWebhookEvent
from app.tenants import service as tenant_service


def _request_with_tenant(tenant_id: str) -> Request:
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "path": "/commercial/subscription",
            "raw_path": b"/commercial/subscription",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "https",
            "root_path": "",
            "app": object(),
            "state": {},
        }
    )
    request.state.header_tenant_id = tenant_id
    return request


class _FakeResult:
    def __init__(self, row: dict[str, object] | None) -> None:
        self._row = row

    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> dict[str, object] | None:
        return self._row

    def one(self) -> dict[str, object]:
        if self._row is None:
            raise AssertionError("expected a row")
        return self._row

    def scalar_one(self):
        if self._row is None:
            raise AssertionError("expected a scalar row")
        if isinstance(self._row, dict):
            values = list(self._row.values())
            return values[0] if values else None
        return self._row

    def scalar_one_or_none(self):
        if self._row is None:
            return None
        return self.scalar_one()


class _FakeSession:
    def __init__(self, row: dict[str, object] | None = None) -> None:
        self.row = row
        self.executed: list[tuple[str, dict[str, object] | None]] = []

    async def execute(self, statement, params: dict[str, object] | None = None):
        self.executed.append((str(statement), params))
        return _FakeResult(self.row)


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeNestedTransaction:
    def __init__(self, session: "_FakeWebhookSession") -> None:
        self.session = session

    async def __aenter__(self) -> "_FakeNestedTransaction":
        self.session.nested_entries += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.session.nested_rollbacks += 1
        else:
            self.session.nested_commits += 1
        return False


class _FakeWebhookSession:
    def __init__(self) -> None:
        self.nested_entries = 0
        self.nested_rollbacks = 0
        self.nested_commits = 0

    def begin_nested(self) -> _FakeNestedTransaction:
        return _FakeNestedTransaction(self)


@pytest.mark.parametrize(
    ("state", "tenant_status", "tenant_is_active"),
    [
        ("trial", "active", True),
        ("active", "active", True),
        ("past_due", "active", True),
        ("grace", "active", True),
        ("suspended", "suspended", False),
        ("canceled", "disabled", False),
    ],
)
def test_commercial_state_maps_to_tenant_access_state(state: str, tenant_status: str, tenant_is_active: bool) -> None:
    mapped_status, mapped_is_active = commercial_service._commercial_state_to_tenant_status(state)  # type: ignore[attr-defined]
    assert mapped_status == tenant_status
    assert mapped_is_active is tenant_is_active


@pytest.mark.asyncio
async def test_commercial_principal_allows_suspended_tenant_for_billing_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expires_at = int(datetime.now(timezone.utc).timestamp()) + 300
    payload = {
        "sub": "user-1",
        "tenant_id": "tenant-1",
        "jti": "access-jti",
        "exp": expires_at,
        "iat": expires_at - 300,
        "iss": "supacrm",
        "aud": "supacrm-api",
        "typ": "access",
        "roles": ["billing"],
    }

    async def _noop_snapshot(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(commercial_deps, "decode_access_token", lambda _: payload)
    monkeypatch.setattr(commercial_deps.auth_cache, "get_principal_snapshot", _noop_snapshot)
    monkeypatch.setattr(commercial_deps.auth_cache, "set_principal_snapshot", _noop_snapshot)
    monkeypatch.setattr(
        commercial_deps,
        "async_session_factory",
        _FakeSessionContext(
            _FakeSession(
                {
                    "tenant_status": "suspended",
                    "tenant_is_active": False,
                    "user_is_active": True,
                    "membership_is_active": True,
                }
            )
        ),
    )

    principal = await commercial_deps.get_commercial_principal(
        _request_with_tenant("tenant-1"),
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token"),
    )

    assert principal["tenant_status"] == "suspended"
    assert principal["tenant_is_active"] is False
    assert principal["user_is_active"] is True


@pytest.mark.asyncio
async def test_change_subscription_state_invalidates_cached_tenant_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    update_row = {
        "id": "sub-1",
        "tenant_id": "tenant-1",
        "plan_id": "plan-1",
        "plan_code": "starter",
        "plan_name": "Starter",
        "provider": "stripe",
        "provider_customer_id": "cus-1",
        "provider_subscription_id": "sub-provider-1",
        "subscription_status": "suspended",
        "commercial_state": "suspended",
        "state_reason": "billing_hold",
        "trial_start_at": None,
        "trial_end_at": None,
        "current_period_start_at": None,
        "current_period_end_at": None,
        "grace_end_at": None,
        "cancel_at_period_end": False,
        "activated_at": None,
        "reactivated_at": None,
        "suspended_at": datetime.now(timezone.utc),
        "canceled_at": None,
        "metadata": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    session = _FakeSession(update_row)
    invalidated: list[str] = []

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_get_billing_event(*_: object, **__: object):
        return None

    async def _fake_invalidate(tenant_id: str) -> None:
        invalidated.append(tenant_id)

    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    updated = await commercial_service.change_subscription_state(
        session,
        subscription_id="sub-1",
        commercial_state="suspended",
        reason="billing_hold",
    )

    assert updated.commercial_state == "suspended"
    assert invalidated == ["tenant-1"]
    assert session.executed, "expected the subscription update to hit the database layer"


@pytest.mark.asyncio
async def test_set_subscription_past_due_uses_plan_grace_days(monkeypatch: pytest.MonkeyPatch) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id=None,
        provider_subscription_id=None,
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    plan = commercial_service.CommercialPlanDetails(
        id="plan-1",
        code="starter",
        name="Starter",
        description=None,
        provider="stripe",
        provider_price_id=None,
        billing_interval="month",
        price_amount=0,
        currency="USD",
        trial_days=14,
        grace_days=11,
        is_active=True,
        features={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    captured: dict[str, object] = {}

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_get_plan_by_id(*_: object, **__: object):
        return plan

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured.update(kwargs)
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service, "get_plan_by_id", _fake_get_plan_by_id)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    before = datetime.now(timezone.utc)
    result = await commercial_service.set_subscription_past_due(
        object(),
        subscription_id="sub-1",
        reason="invoice_failed",
    )

    assert result == subscription
    assert captured["commercial_state"] == "past_due"
    assert captured["grace_end_at"] is not None
    assert (captured["grace_end_at"] - before).total_seconds() >= 11 * 24 * 3600 - 5
    assert (captured["grace_end_at"] - before).total_seconds() <= 11 * 24 * 3600 + 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("event_type", "expected_state"),
    [
        ("customer.subscription.created", "trial"),
        ("customer.subscription.updated", "active"),
        ("customer.subscription.deleted", "canceled"),
        ("invoice.payment_succeeded", "active"),
        ("invoice.payment_failed", "past_due"),
    ],
)
async def test_process_provider_event_maps_webhook_to_state_changes(
    monkeypatch: pytest.MonkeyPatch,
    event_type: str,
    expected_state: str,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    plan = commercial_service.CommercialPlanDetails(
        id="plan-1",
        code="starter",
        name="Starter",
        description=None,
        provider="stripe",
        provider_price_id=None,
        billing_interval="month",
        price_amount=0,
        currency="USD",
        trial_days=14,
        grace_days=11,
        is_active=True,
        features={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    captured: dict[str, object] = {}

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_get_plan_by_id(*_: object, **__: object):
        return plan

    async def _fake_get_subscription_by_tenant(*_: object, **__: object):
        return subscription

    async def _fake_get_billing_event(*_: object, **__: object):
        return None

    async def _fake_billing_event(*_: object, **kwargs: object):
        captured["billing_status"] = kwargs.get("processing_status")
        return commercial_service.CommercialBillingEventDetails(
            id="evt-db",
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            provider="stripe",
            external_event_id=str(kwargs.get("external_event_id")),
            event_type=str(kwargs.get("event_type")),
            processing_status=str(kwargs.get("processing_status")),
            action_taken=kwargs.get("action_taken"),
            error_message=kwargs.get("error_message"),
            raw_payload=dict(kwargs.get("raw_payload") or {}),
            processed_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured["state"] = kwargs.get("commercial_state")
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_get_subscription_by_tenant)
    monkeypatch.setattr(commercial_service, "get_billing_event_by_external_event_id", _fake_get_billing_event)
    monkeypatch.setattr(commercial_service, "get_plan_by_id", _fake_get_plan_by_id)
    monkeypatch.setattr(commercial_service, "ensure_billing_event", _fake_billing_event)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    payload_object: dict[str, object] = {
        "metadata": {"tenant_id": "tenant-1", "subscription_id": "sub-1"},
        "status": "trialing" if event_type == "customer.subscription.created" else "active",
        "current_period_start": int(datetime.now(timezone.utc).timestamp()),
        "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 3600,
    }
    payload = {
        "id": "evt_123",
        "type": event_type,
        "data": {"object": payload_object},
    }
    event = CommercialWebhookEvent(
        provider="stripe",
        event_id="evt_123",
        event_type=event_type,
        raw_payload=payload,
        customer_id="cus-1",
        subscription_id="sub-provider-1",
    )

    await commercial_service.process_provider_event(_FakeWebhookSession(), event)

    assert captured["billing_status"] == "processed"
    assert captured["state"] == expected_state


@pytest.mark.asyncio
async def test_bootstrap_tenant_creates_commercial_subscription(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    async def _fake_ensure_tenant(*_: object, **__: object):
        return SimpleNamespace(tenant_id="tenant-1", tenant_name="Tenant 1", created_tenant=True)

    async def _fake_seed_rbac(*_: object, **__: object):
        return SimpleNamespace(role_ids_by_name={"owner": "role-owner", "admin": "role-admin"})

    async def _fake_provision_user(*_: object, **__: object):
        user = UserProvisionResult(
            user_id="user-1",
            email="admin@example.com",
            created_user=True,
            created_credentials=True,
            password_set=True,
        )
        membership = SimpleNamespace(tenant_id="tenant-1", user_id="user-1", created_membership=True, is_owner=True)
        return SimpleNamespace(user=user, membership=membership, role_assignments=[])

    async def _fake_plan(*_: object, **__: object):
        return commercial_service.CommercialPlanDetails(
            id="plan-1",
            code="starter",
            name="Starter",
            description=None,
            provider="stripe",
            provider_price_id=None,
            billing_interval="month",
            price_amount=0,
            currency="USD",
            trial_days=14,
            grace_days=7,
            is_active=True,
            features={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_subscription(*_: object, **kwargs: object):
        calls.update(kwargs)
        return commercial_service.CommercialSubscriptionDetails(
            id="sub-1",
            tenant_id=str(kwargs["tenant_id"]),
            plan_id="plan-1",
            plan_code="starter",
            plan_name="Starter",
            provider="stripe",
            provider_customer_id=None,
            provider_subscription_id=None,
            subscription_status="trial",
            commercial_state="trial",
            state_reason=None,
            trial_start_at=datetime.now(timezone.utc),
            trial_end_at=datetime.now(timezone.utc),
            current_period_start_at=datetime.now(timezone.utc),
            current_period_end_at=datetime.now(timezone.utc),
            grace_end_at=None,
            cancel_at_period_end=False,
            activated_at=datetime.now(timezone.utc),
            reactivated_at=None,
            suspended_at=None,
            canceled_at=None,
            metadata={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(tenant_service, "ensure_tenant", _fake_ensure_tenant)
    monkeypatch.setattr(tenant_service, "seed_default_rbac", _fake_seed_rbac)
    monkeypatch.setattr(tenant_service, "provision_tenant_user", _fake_provision_user)
    monkeypatch.setattr(tenant_service, "ensure_default_plan", _fake_plan)
    monkeypatch.setattr(tenant_service, "bootstrap_tenant_subscription", _fake_subscription)

    result = await tenant_service.bootstrap_tenant(
        session=_FakeSession(),
        tenant_id="tenant-1",
        tenant_name="Tenant 1",
        admin_email="admin@example.com",
        admin_full_name="Admin",
        admin_password=None,
    )

    assert result.tenant.tenant_id == "tenant-1"
    assert calls["tenant_id"] == "tenant-1"
    assert calls["plan_code"] == "starter"
    assert calls["start_trial"] is True


@pytest.mark.asyncio
async def test_subscription_lifecycle_helpers_delegate_expected_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    captured: list[tuple[str, dict[str, object]]] = []

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured.append((str(kwargs.get("commercial_state")), dict(kwargs)))
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    await commercial_service.mark_subscription_grace(object(), subscription_id="sub-1", reason="invoice_failed")
    await commercial_service.suspend_subscription(object(), subscription_id="sub-1", reason="suspension")
    await commercial_service.reactivate_subscription(object(), subscription_id="sub-1", reason="reactivation")
    await commercial_service.cancel_subscription(object(), subscription_id="sub-1", reason="canceled")

    assert [state for state, _ in captured] == ["grace", "suspended", "active", "canceled"]
    assert captured[0][1]["grace_end_at"] is not None
    assert captured[1][1]["reason"] == "suspension"
    assert captured[2][1]["reason"] == "reactivation"
    assert captured[3][1]["reason"] == "canceled"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_status", "expected_state"),
    [
        ("unpaid", "past_due"),
        ("paused", "suspended"),
    ],
)
async def test_process_provider_event_maps_provider_statuses_to_commercial_states(
    monkeypatch: pytest.MonkeyPatch,
    provider_status: str,
    expected_state: str,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    captured: dict[str, object] = {}

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_get_billing_event(*_: object, **__: object):
        return None

    async def _fake_billing_event(*_: object, **kwargs: object):
        captured["billing_status"] = kwargs.get("processing_status")
        return commercial_service.CommercialBillingEventDetails(
            id="evt-db",
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            provider="stripe",
            external_event_id=str(kwargs.get("external_event_id")),
            event_type=str(kwargs.get("event_type")),
            processing_status=str(kwargs.get("processing_status")),
            action_taken=kwargs.get("action_taken"),
            error_message=kwargs.get("error_message"),
            raw_payload=dict(kwargs.get("raw_payload") or {}),
            processed_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured["state"] = kwargs.get("commercial_state")
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service, "get_billing_event_by_external_event_id", _fake_get_billing_event)
    monkeypatch.setattr(commercial_service, "ensure_billing_event", _fake_billing_event)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    payload = {
        "id": "evt_123",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "metadata": {"tenant_id": "tenant-1", "subscription_id": "sub-1"},
                "status": provider_status,
                "current_period_start": int(datetime.now(timezone.utc).timestamp()),
                "current_period_end": int(datetime.now(timezone.utc).timestamp()) + 3600,
            }
        },
    }
    event = CommercialWebhookEvent(
        provider="stripe",
        event_id="evt_123",
        event_type="customer.subscription.updated",
        raw_payload=payload,
        customer_id="cus-1",
        subscription_id="sub-provider-1",
    )

    await commercial_service.process_provider_event(_FakeWebhookSession(), event)

    assert captured["billing_status"] == "processed"
    assert captured["state"] == expected_state


@pytest.mark.asyncio
async def test_process_provider_event_payment_failed_marks_subscription_past_due_with_plan_grace_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=fixed_now,
        updated_at=fixed_now,
    )
    plan = commercial_service.CommercialPlanDetails(
        id="plan-1",
        code="starter",
        name="Starter",
        description=None,
        provider="stripe",
        provider_price_id="price_starter",
        billing_interval="month",
        price_amount=49,
        currency="USD",
        trial_days=14,
        grace_days=9,
        is_active=True,
        features={},
        created_at=fixed_now,
        updated_at=fixed_now,
    )
    captured: dict[str, object] = {}

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_get_billing_event(*_: object, **__: object):
        return None

    async def _fake_ensure_billing_event(*_: object, **kwargs: object):
        captured.setdefault("billing_statuses", []).append(kwargs.get("processing_status"))
        return commercial_service.CommercialBillingEventDetails(
            id="evt-db",
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            provider="stripe",
            external_event_id=str(kwargs.get("external_event_id")),
            event_type=str(kwargs.get("event_type")),
            processing_status=str(kwargs.get("processing_status")),
            action_taken=kwargs.get("action_taken"),
            error_message=kwargs.get("error_message"),
            raw_payload=dict(kwargs.get("raw_payload") or {}),
            processed_at=None,
            created_at=fixed_now,
            updated_at=fixed_now,
        )

    async def _fake_get_plan_by_id(*_: object, **__: object):
        return plan

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured["change_kwargs"] = kwargs
        return subscription

    monkeypatch.setattr(commercial_service, "_now", lambda: fixed_now)
    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service, "get_billing_event_by_external_event_id", _fake_get_billing_event)
    monkeypatch.setattr(commercial_service, "ensure_billing_event", _fake_ensure_billing_event)
    monkeypatch.setattr(commercial_service, "get_plan_by_id", _fake_get_plan_by_id)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    event = CommercialWebhookEvent(
        provider="stripe",
        event_id="evt_payment_failed",
        event_type="invoice.payment_failed",
        raw_payload={
            "id": "evt_payment_failed",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "metadata": {"tenant_id": "tenant-1", "subscription_id": "sub-1"},
                    "subscription": "sub-provider-1",
                }
            },
        },
        customer_id="cus-1",
        subscription_id="sub-provider-1",
    )

    await commercial_service.process_provider_event(_FakeWebhookSession(), event)

    assert captured["billing_statuses"] == ["processing", "processed"]
    change_kwargs = captured["change_kwargs"]
    assert change_kwargs["subscription_status"] == "past_due"
    assert change_kwargs["commercial_state"] == "past_due"
    assert change_kwargs["reason"] == "invoice_payment_failed"
    assert change_kwargs["grace_end_at"] == fixed_now + timedelta(days=9)


@pytest.mark.asyncio
async def test_process_provider_event_rolls_back_local_mutation_and_records_failed_checkout_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=fixed_now,
        updated_at=fixed_now,
    )
    captured: dict[str, object] = {"billing_statuses": []}

    async def _fake_get_subscription_by_id(*_: object, **__: object):
        return subscription

    async def _fake_get_billing_event(*_: object, **__: object):
        return None

    async def _fake_ensure_billing_event(*_: object, **kwargs: object):
        captured["billing_statuses"].append(kwargs.get("processing_status"))
        return commercial_service.CommercialBillingEventDetails(
            id="evt-db",
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            provider="stripe",
            external_event_id=str(kwargs.get("external_event_id")),
            event_type=str(kwargs.get("event_type")),
            processing_status=str(kwargs.get("processing_status")),
            action_taken=kwargs.get("action_taken"),
            error_message=kwargs.get("error_message"),
            raw_payload=dict(kwargs.get("raw_payload") or {}),
            processed_at=None,
            created_at=fixed_now,
            updated_at=fixed_now,
        )

    class _Provider:
        async def get_setup_intent(self, **_: object):
            return {"id": "seti_123"}

    async def _fake_provider_client(*_: object, **__: object):
        return _Provider()

    async def _fake_change_subscription_state(*_: object, **__: object):
        captured["change_calls"] = int(captured.get("change_calls", 0)) + 1
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_id", _fake_get_subscription_by_id)
    monkeypatch.setattr(commercial_service, "get_billing_event_by_external_event_id", _fake_get_billing_event)
    monkeypatch.setattr(commercial_service, "ensure_billing_event", _fake_ensure_billing_event)
    monkeypatch.setattr(commercial_service, "_get_tenant_provider_client", _fake_provider_client)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    session = _FakeWebhookSession()
    event = CommercialWebhookEvent(
        provider="stripe",
        event_id="evt_checkout_failed",
        event_type="checkout.session.completed",
        raw_payload={
            "id": "evt_checkout_failed",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "mode": "setup",
                    "customer": "cus-1",
                    "setup_intent": "seti_123",
                    "metadata": {"tenant_id": "tenant-1", "subscription_id": "sub-1"},
                }
            },
        },
        customer_id="cus-1",
        subscription_id="sub-provider-1",
    )

    result = await commercial_service.process_provider_event(session, event)

    assert result.processing_status == "failed"
    assert "payment method" in str(result.error_message).lower()
    assert captured["billing_statuses"] == ["processing", "failed"]
    assert captured["change_calls"] == 1
    assert session.nested_rollbacks == 1
    assert session.nested_commits == 0


@pytest.mark.asyncio
async def test_bootstrap_tenant_subscription_uses_trial_without_external_customer_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = commercial_service.CommercialPlanDetails(
        id="plan-1",
        code="starter",
        name="Starter",
        description=None,
        provider="stripe",
        provider_price_id=None,
        billing_interval="month",
        price_amount=0,
        currency="USD",
        trial_days=14,
        grace_days=7,
        is_active=True,
        features={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session = _FakeSession(
        {
            "id": "sub-1",
            "tenant_id": "tenant-1",
            "plan_id": "plan-1",
            "plan_code": "starter",
            "plan_name": "Starter",
            "provider": "stripe",
            "provider_customer_id": None,
            "provider_subscription_id": None,
            "commercial_state": "trial",
            "state_reason": None,
            "trial_start_at": datetime.now(timezone.utc),
            "trial_end_at": datetime.now(timezone.utc),
            "current_period_start_at": datetime.now(timezone.utc),
            "current_period_end_at": datetime.now(timezone.utc),
            "grace_end_at": None,
            "cancel_at_period_end": False,
            "activated_at": datetime.now(timezone.utc),
            "reactivated_at": None,
            "suspended_at": None,
            "canceled_at": None,
            "metadata": {},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    provider_calls: list[str] = []

    class _Provider:
        async def create_customer(self, **_: object) -> str:
            provider_calls.append("customer")
            raise AssertionError("customer creation should not run for trial-only bootstrap")

        async def create_subscription(self, **_: object):
            provider_calls.append("subscription")
            raise AssertionError("subscription creation should not run for trial-only bootstrap")

    async def _fake_get_plan_by_code(*_: object, **__: object):
        return plan

    monkeypatch.setattr(commercial_service, "get_plan_by_code", _fake_get_plan_by_code)
    monkeypatch.setattr(commercial_service, "get_commercial_provider", lambda *_: _Provider())
    invalidated: list[str] = []

    async def _fake_invalidate(tenant_id: str) -> None:
        invalidated.append(tenant_id)

    monkeypatch.setattr(commercial_service.auth_cache, "invalidate_snapshots_for_tenant", _fake_invalidate)

    subscription = await commercial_service.bootstrap_tenant_subscription(
        session,
        tenant_id="tenant-1",
        plan_code="starter",
        provider="stripe",
        start_trial=True,
        customer_email="admin@example.com",
        customer_name="Admin",
        metadata={"bootstrapped": True},
    )

    assert subscription.commercial_state == "trial"
    assert provider_calls == []
    assert invalidated == ["tenant-1"]


@pytest.mark.asyncio
async def test_bootstrap_tenant_subscription_requires_enabled_provider_for_automated_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = commercial_service.CommercialPlanDetails(
        id="plan-2",
        code="growth",
        name="Growth",
        description=None,
        provider="stripe",
        provider_price_id="price_growth",
        billing_interval="month",
        price_amount=49,
        currency="USD",
        trial_days=14,
        grace_days=7,
        is_active=True,
        features={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def _fake_get_plan_by_code(*_: object, **__: object):
        return plan

    async def _fake_get_gateway_record(*_: object, **__: object):
        return SimpleNamespace(
            provider="stripe",
            is_enabled=False,
            configuration_state="configured",
            secret_key="sk_tenant",
            api_key=None,
            client_secret=None,
            webhook_secret="whsec_tenant",
            publishable_key="pk_tenant",
            account_id=None,
            merchant_id=None,
            client_id=None,
            mode="live",
        )

    monkeypatch.setattr(commercial_service, "get_plan_by_code", _fake_get_plan_by_code)
    monkeypatch.setattr(
        commercial_service,
        "get_payment_gateway_provider_record",
        _fake_get_gateway_record,
    )

    with pytest.raises(ValueError, match="Payment provider is not enabled for tenant: stripe"):
        await commercial_service.bootstrap_tenant_subscription(
            _FakeSession(),
            tenant_id="tenant-1",
            plan_code="growth",
            provider="stripe",
            start_trial=False,
            customer_email="billing@example.com",
            customer_name="Billing Owner",
        )


@pytest.mark.asyncio
async def test_bootstrap_tenant_subscription_uses_tenant_scoped_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = commercial_service.CommercialPlanDetails(
        id="plan-3",
        code="scale",
        name="Scale",
        description=None,
        provider="stripe",
        provider_price_id="price_scale",
        billing_interval="month",
        price_amount=149,
        currency="USD",
        trial_days=14,
        grace_days=7,
        is_active=True,
        features={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    provider_calls: dict[str, object] = {}

    async def _fake_get_plan_by_code(*_: object, **__: object):
        return plan

    async def _fake_get_gateway_record(*_: object, **__: object):
        return SimpleNamespace(
            provider="stripe",
            is_enabled=True,
            configuration_state="configured",
            secret_key="sk_tenant_scoped",
            api_key=None,
            client_secret=None,
            webhook_secret="whsec_tenant_scoped",
            publishable_key="pk_tenant_scoped",
            account_id=None,
            merchant_id=None,
            client_id=None,
            mode="live",
        )

    class _Provider:
        async def create_customer(self, **kwargs: object) -> str:
            provider_calls["customer"] = kwargs
            return "cus_tenant_scoped"

        async def create_subscription(self, **kwargs: object):
            provider_calls["subscription"] = kwargs
            return commercial_service.CommercialProviderSubscriptionResult(
                provider="stripe",
                provider_customer_id="cus_tenant_scoped",
                provider_subscription_id="sub_tenant_scoped",
                status="active",
                trial_end_at=datetime.now(timezone.utc),
                current_period_start_at=datetime.now(timezone.utc),
                current_period_end_at=datetime.now(timezone.utc),
                cancel_at_period_end=False,
                raw={"source": "tenant_gateway_settings"},
            )

    def _fake_get_commercial_provider(provider: str, *, config: dict[str, object] | None = None):
        provider_calls["provider"] = provider
        provider_calls["config"] = config
        return _Provider()

    async def _fake_upsert_subscription(*_: object, **kwargs: object):
        return commercial_service.CommercialSubscriptionDetails(
            id="sub-tenant-scoped",
            tenant_id=str(kwargs["tenant_id"]),
            plan_id=str(kwargs["plan_id"]),
            plan_code=plan.code,
            plan_name=plan.name,
            provider=str(kwargs["provider"]),
            provider_customer_id=kwargs["provider_customer_id"],
            provider_subscription_id=kwargs["provider_subscription_id"],
            subscription_status=kwargs["subscription_status"],
            commercial_state=str(kwargs["commercial_state"]),
            state_reason=kwargs["state_reason"],
            trial_start_at=kwargs["trial_start_at"],
            trial_end_at=kwargs["trial_end_at"],
            current_period_start_at=kwargs["current_period_start_at"],
            current_period_end_at=kwargs["current_period_end_at"],
            grace_end_at=kwargs["grace_end_at"],
            cancel_at_period_end=bool(kwargs["cancel_at_period_end"]),
            activated_at=kwargs["activated_at"],
            reactivated_at=kwargs["reactivated_at"],
            suspended_at=kwargs["suspended_at"],
            canceled_at=kwargs["canceled_at"],
            metadata=dict(kwargs["metadata"]),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def _fake_set_tenant_access_state(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(commercial_service, "get_plan_by_code", _fake_get_plan_by_code)
    monkeypatch.setattr(
        commercial_service,
        "get_payment_gateway_provider_record",
        _fake_get_gateway_record,
    )
    monkeypatch.setattr(
        commercial_service,
        "get_commercial_provider",
        _fake_get_commercial_provider,
    )
    async def _fake_default_payment_method(*_: object, **__: object):
        return SimpleNamespace(provider_payment_method_id="pm_default")

    monkeypatch.setattr(commercial_service, "get_default_payment_method", _fake_default_payment_method)
    monkeypatch.setattr(commercial_service, "_upsert_subscription", _fake_upsert_subscription)
    monkeypatch.setattr(
        commercial_service,
        "_set_tenant_access_state",
        _fake_set_tenant_access_state,
    )

    subscription = await commercial_service.bootstrap_tenant_subscription(
        _FakeSession(),
        tenant_id="tenant-1",
        plan_code="scale",
        provider="stripe",
        start_trial=False,
        customer_email="billing@example.com",
        customer_name="Billing Owner",
    )

    assert provider_calls["provider"] == "stripe"
    assert provider_calls["config"] == {
        "secret_key": "sk_tenant_scoped",
        "api_key": None,
        "client_secret": None,
        "webhook_secret": "whsec_tenant_scoped",
        "publishable_key": "pk_tenant_scoped",
        "account_id": None,
        "merchant_id": None,
        "client_id": None,
        "mode": "live",
    }
    assert subscription.provider_customer_id == "cus_tenant_scoped"
    assert subscription.provider_subscription_id == "sub_tenant_scoped"


@pytest.mark.asyncio
async def test_process_provider_event_is_idempotent_for_processed_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed_event = commercial_service.CommercialBillingEventDetails(
        id="evt-db",
        tenant_id="tenant-1",
        subscription_id="sub-1",
        provider="stripe",
        external_event_id="evt_123",
        event_type="customer.subscription.updated",
        processing_status="processed",
        action_taken="active",
        error_message=None,
        raw_payload={},
        processed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    async def _fake_existing_event(*_: object, **__: object):
        return processed_event

    async def _unexpected(*_: object, **__: object):
        raise AssertionError("idempotent webhook processing should not re-run mutations")

    monkeypatch.setattr(commercial_service, "get_billing_event_by_external_event_id", _fake_existing_event)
    monkeypatch.setattr(commercial_service, "ensure_billing_event", _unexpected)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _unexpected)

    event = CommercialWebhookEvent(
        provider="stripe",
        event_id="evt_123",
        event_type="customer.subscription.updated",
        raw_payload={"id": "evt_123", "type": "customer.subscription.updated", "data": {"object": {"metadata": {}}}},
    )

    result = await commercial_service.process_provider_event(object(), event)

    assert result.processing_status == "processed"
    assert result.action_taken == "active"


@pytest.mark.asyncio
async def test_create_payment_method_checkout_session_creates_customer_and_returns_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-1",
        plan_code="growth",
        plan_name="Growth",
        provider="stripe",
        provider_customer_id=None,
        provider_subscription_id="sub-provider-1",
        subscription_status="trialing",
        commercial_state="trial",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    captured: dict[str, object] = {}

    class _Provider:
        async def create_customer(self, **kwargs: object) -> str:
            captured["customer"] = kwargs
            return "cus_created"

        async def create_checkout_session(self, **kwargs: object):
            captured["checkout"] = kwargs
            return SimpleNamespace(
                provider="stripe",
                session_id="cs_123",
                url="https://stripe.test/setup",
                mode="setup",
                provider_customer_id="cus_created",
                provider_subscription_id=None,
            )

    async def _fake_subscription(*_: object, **__: object):
        return subscription

    async def _fake_provider_client(*_: object, **__: object):
        return _Provider()

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured["provider_customer_id"] = kwargs.get("provider_customer_id")
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_subscription)
    monkeypatch.setattr(commercial_service, "_get_tenant_provider_client", _fake_provider_client)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    result = await commercial_service.create_payment_method_checkout_session(
        object(),
        tenant_id="tenant-1",
        customer_email="owner@example.com",
        customer_name="Owner",
    )

    assert captured["provider_customer_id"] == "cus_created"
    assert captured["customer"] == {
        "email": "owner@example.com",
        "metadata": {
            "tenant_id": "tenant-1",
            "subscription_id": "sub-1",
            "customer_name": "Owner",
        },
    }
    assert captured["checkout"]["customer_id"] == "cus_created"
    assert result.url == "https://stripe.test/setup"


@pytest.mark.asyncio
async def test_change_subscription_plan_waits_for_webhook_before_local_plan_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-growth",
        plan_code="growth",
        plan_name="Growth",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    new_plan = commercial_service.CommercialPlanDetails(
        id="plan-scale",
        code="scale",
        name="Scale",
        description=None,
        provider="stripe",
        provider_price_id="price_scale",
        billing_interval="month",
        price_amount=149,
        currency="USD",
        trial_days=14,
        grace_days=7,
        is_active=True,
        features={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    captured: dict[str, object] = {}

    class _Provider:
        async def update_subscription(self, **kwargs: object):
            captured["provider_update"] = kwargs
            return commercial_service.CommercialProviderSubscriptionResult(
                provider="stripe",
                provider_customer_id="cus-1",
                provider_subscription_id="sub-provider-1",
                status="active",
                trial_end_at=None,
                current_period_start_at=datetime.now(timezone.utc),
                current_period_end_at=datetime.now(timezone.utc),
                cancel_at_period_end=False,
                raw={},
            )

    async def _fake_get_subscription(*_: object, **__: object):
        return subscription

    async def _fake_get_plan(*_: object, **__: object):
        return new_plan

    async def _fake_provider_client(*_: object, **__: object):
        return _Provider()

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured["change"] = kwargs
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_get_subscription)
    monkeypatch.setattr(commercial_service, "get_plan_by_code", _fake_get_plan)
    monkeypatch.setattr(commercial_service, "_get_tenant_provider_client", _fake_provider_client)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    await commercial_service.change_subscription_plan(
        object(),
        tenant_id="tenant-1",
        new_plan_code="scale",
        prorate=True,
    )

    assert captured["provider_update"]["price_id"] == "price_scale"
    assert "plan_id" not in captured["change"]
    assert captured["change"]["reason"] == "awaiting_stripe_plan_change_confirmation"


@pytest.mark.asyncio
async def test_request_subscription_cancellation_uses_stripe_period_end_and_waits_for_webhook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-growth",
        plan_code="growth",
        plan_name="Growth",
        provider="stripe",
        provider_customer_id="cus-1",
        provider_subscription_id="sub-provider-1",
        subscription_status="active",
        commercial_state="active",
        state_reason=None,
        trial_start_at=None,
        trial_end_at=None,
        current_period_start_at=None,
        current_period_end_at=None,
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=None,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    captured: dict[str, object] = {}

    class _Provider:
        async def cancel_subscription(self, **kwargs: object):
            captured["cancel"] = kwargs
            return commercial_service.CommercialProviderSubscriptionResult(
                provider="stripe",
                provider_customer_id="cus-1",
                provider_subscription_id="sub-provider-1",
                status="active",
                trial_end_at=None,
                current_period_start_at=datetime.now(timezone.utc),
                current_period_end_at=datetime.now(timezone.utc),
                cancel_at_period_end=True,
                raw={},
            )

    async def _fake_get_subscription(*_: object, **__: object):
        return subscription

    async def _fake_provider_client(*_: object, **__: object):
        return _Provider()

    async def _fake_change_subscription_state(*_: object, **kwargs: object):
        captured["change"] = kwargs
        return subscription

    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_get_subscription)
    monkeypatch.setattr(commercial_service, "_get_tenant_provider_client", _fake_provider_client)
    monkeypatch.setattr(commercial_service, "change_subscription_state", _fake_change_subscription_state)

    await commercial_service.request_subscription_cancellation(object(), tenant_id="tenant-1")

    assert captured["cancel"] == {
        "subscription_id": "sub-provider-1",
        "cancel_at_period_end": True,
    }
    assert captured["change"]["cancel_at_period_end"] is True
    assert captured["change"]["reason"] == "awaiting_stripe_cancellation_confirmation"
