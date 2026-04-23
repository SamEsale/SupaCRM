from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from starlette.requests import Request

from app.auth import routes as auth_routes
from app.auth.schemas import RegisterRequest
from app.auth.service import RegisterTenantResult, TokenPairResult
from app.commercial import routes as commercial_routes
from app.commercial import service as commercial_service


class _BeginContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _AdminSession:
    def begin(self) -> _BeginContext:
        return _BeginContext()


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "path": path,
            "raw_path": path.encode(),
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


def _plan(*, code: str = "starter", billing_interval: str = "month") -> commercial_service.CommercialPlanDetails:
    now = datetime.now(timezone.utc)
    return commercial_service.CommercialPlanDetails(
        id=f"plan-{code}",
        code=code,
        name="Starter" if code == "starter" else "Starter Yearly",
        description="Starter commercial plan",
        provider="stripe",
        provider_price_id=None,
        billing_interval=billing_interval,
        price_amount=0,
        currency="USD",
        trial_days=14,
        grace_days=7,
        is_active=True,
        features={"included_capabilities": ["CRM core", "Billing visibility"]},
        created_at=now,
        updated_at=now,
    )


def _subscription() -> commercial_service.CommercialSubscriptionDetails:
    now = datetime.now(timezone.utc)
    return commercial_service.CommercialSubscriptionDetails(
        id="sub-1",
        tenant_id="tenant-1",
        plan_id="plan-starter",
        plan_code="starter",
        plan_name="Starter",
        provider="stripe",
        provider_customer_id="cus_123",
        provider_subscription_id="sub_123",
        subscription_status="trial",
        commercial_state="trial",
        state_reason=None,
        trial_start_at=now,
        trial_end_at=now + timedelta(days=14),
        current_period_start_at=now,
        current_period_end_at=now + timedelta(days=14),
        grace_end_at=None,
        cancel_at_period_end=False,
        activated_at=now,
        reactivated_at=None,
        suspended_at=None,
        canceled_at=None,
        metadata={},
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_get_tenant_commercial_status_reports_current_plan_and_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subscription = _subscription()
    plan = _plan()

    async def _noop_ensure_catalog(*_: object, **__: object) -> list[commercial_service.CommercialPlanDetails]:
        return [plan]

    async def _fake_get_subscription(*_: object, **__: object):
        return subscription

    async def _fake_get_plan(*_: object, **__: object):
        return plan

    monkeypatch.setattr(commercial_service, "ensure_plan_catalog", _noop_ensure_catalog)
    monkeypatch.setattr(commercial_service, "get_subscription_by_tenant", _fake_get_subscription)
    monkeypatch.setattr(commercial_service, "get_plan_by_id", _fake_get_plan)

    status = await commercial_service.get_tenant_commercial_status(object(), tenant_id="tenant-1")

    assert status.current_plan is not None
    assert status.current_plan.code == "starter"
    assert status.subscription_status == "trial"
    assert status.trial_status == "active"
    assert status.provider_name == "Stripe"
    assert status.commercially_active is True
    assert status.next_billing_at == subscription.current_period_end_at


@pytest.mark.asyncio
async def test_public_catalog_route_exposes_plan_code_and_features_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _noop_ensure_catalog(*_: object, **__: object) -> list[commercial_service.CommercialPlanDetails]:
        return []

    async def _fake_list_plans(*_: object, **__: object) -> list[commercial_service.CommercialPlanDetails]:
        return [_plan(code="starter", billing_interval="month"), _plan(code="starter_yearly", billing_interval="year")]

    monkeypatch.setattr(commercial_routes, "ensure_plan_catalog", _noop_ensure_catalog)
    monkeypatch.setattr(commercial_routes, "list_plans", _fake_list_plans)

    catalog = await commercial_routes.list_public_commercial_catalog_route(db=_AdminSession())

    assert [plan.plan_code for plan in catalog] == ["starter", "starter_yearly"]
    assert catalog[0].features_summary == ["CRM core", "Billing visibility"]


@pytest.mark.asyncio
async def test_register_route_returns_bootstrapped_tenant_tokens_and_commercial_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    token_pair = TokenPairResult(
        access_token="access-token",
        refresh_token="refresh-token",
        tenant_id="tenant-1",
        access_token_expires_at=now + timedelta(minutes=15),
        refresh_token_expires_at=now + timedelta(days=30),
    )
    plan = _plan()
    subscription = _subscription()
    commercial_status = commercial_service.TenantCommercialStatus(
        current_plan=plan,
        subscription=subscription,
        subscription_status="trial",
        trial_status="active",
        next_billing_at=subscription.current_period_end_at,
        renewal_at=subscription.current_period_end_at,
        provider="stripe",
        provider_name="Stripe",
        provider_customer_id=subscription.provider_customer_id,
        provider_subscription_id=subscription.provider_subscription_id,
        commercially_active=True,
    )
    captured: dict[str, object] = {}

    async def _fake_register_tenant_admin(**kwargs: object) -> RegisterTenantResult:
        captured.update(kwargs)
        return RegisterTenantResult(
            token_pair=token_pair,
            tenant_id="tenant-1",
            tenant_name="Acme",
            commercial_status=commercial_status,
        )

    monkeypatch.setattr(auth_routes, "register_tenant_admin", _fake_register_tenant_admin)

    response = await auth_routes.register(
        RegisterRequest(
            company_name="Acme",
            full_name="Owner User",
            email="owner@example.com",
            password="Password1234!",
            plan_code="starter",
            provider="stripe",
            start_trial=True,
        ),
        _request("/auth/register"),
    )

    assert captured["plan_code"] == "starter"
    assert response.tenant_id == "tenant-1"
    assert response.tenant_name == "Acme"
    assert response.commercial_status.current_plan is not None
    assert response.commercial_status.current_plan.plan_code == "starter"
    assert response.commercial_status.commercially_active is True
