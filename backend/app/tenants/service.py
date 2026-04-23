from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import UserProvisionResult, provision_user
from app.core.security.auth_cache import auth_cache
from app.commercial import service as commercial_service
from app.commercial.service import bootstrap_tenant_subscription, ensure_default_plan, ensure_plan_catalog
from app.db import reset_tenant_guc, set_tenant_guc
from app.integrations.storage.service import presign_download_url
from app.rbac.service import RbacSeedResult, seed_default_rbac

TENANT_PROFILE_COLUMNS: tuple[str, ...] = (
    "legal_name",
    "address_line_1",
    "address_line_2",
    "city",
    "state_region",
    "postal_code",
    "country",
    "vat_number",
    "default_currency",
    "secondary_currency",
    "secondary_currency_rate",
    "secondary_currency_rate_source",
    "secondary_currency_rate_as_of",
    "brand_primary_color",
    "brand_secondary_color",
    "sidebar_background_color",
    "sidebar_text_color",
)

TENANT_OPTIONAL_DETAIL_COLUMNS: tuple[str, ...] = ("logo_file_key", *TENANT_PROFILE_COLUMNS)
TENANT_BRANDING_COLUMNS: tuple[str, ...] = (
    "logo_file_key",
    "brand_primary_color",
    "brand_secondary_color",
    "sidebar_background_color",
    "sidebar_text_color",
)
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-F]{6}$")


@dataclass(slots=True)
class TenantProvisionResult:
    tenant_id: str
    tenant_name: str
    created_tenant: bool


@dataclass(slots=True)
class MembershipProvisionResult:
    tenant_id: str
    user_id: str
    created_membership: bool
    is_owner: bool


@dataclass(slots=True)
class RoleAssignmentResult:
    role_name: str
    role_id: str
    created_assignment: bool


@dataclass(slots=True)
class TenantUserProvisionResult:
    tenant_id: str
    user: UserProvisionResult
    membership: MembershipProvisionResult
    role_assignments: list[RoleAssignmentResult] = field(default_factory=list)


AdminProvisionResult = TenantUserProvisionResult


@dataclass(slots=True)
class TenantBootstrapResult:
    tenant: TenantProvisionResult
    rbac: RbacSeedResult
    admin: TenantUserProvisionResult


@dataclass(slots=True)
class TenantOnboardingCommercialSummary:
    id: str
    plan_code: str
    plan_name: str
    commercial_state: str
    plan_features: dict[str, object]
    trial_end_at: datetime | None
    current_period_end_at: datetime | None
    grace_end_at: datetime | None
    canceled_at: datetime | None


@dataclass(slots=True)
class TenantOnboardingSummary:
    tenant: TenantDetails
    commercial_subscription: TenantOnboardingCommercialSummary | None
    users_total: int
    owner_count: int
    admin_count: int
    bootstrap_complete: bool
    ready_for_use: bool
    missing_steps: list[str]
    warnings: list[str]
    next_action: str


@dataclass(slots=True)
class TenantDetails:
    id: str
    name: str
    is_active: bool
    status: str
    status_reason: str | None
    legal_name: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    state_region: str | None
    postal_code: str | None
    country: str | None
    vat_number: str | None
    default_currency: str | None
    secondary_currency: str | None
    secondary_currency_rate: Decimal | None
    secondary_currency_rate_source: str | None
    secondary_currency_rate_as_of: datetime | None
    brand_primary_color: str | None
    brand_secondary_color: str | None
    sidebar_background_color: str | None
    sidebar_text_color: str | None
    created_at: datetime
    updated_at: datetime
    logo_file_key: str | None = None


@dataclass(slots=True)
class TenantBrandingDetails:
    tenant_id: str
    logo_file_key: str | None
    logo_url: str | None
    brand_primary_color: str | None
    brand_secondary_color: str | None
    sidebar_background_color: str | None
    sidebar_text_color: str | None


@dataclass(slots=True)
class TenantRoleSummary:
    id: str
    name: str
    permission_codes: list[str]
    created_at: datetime


@dataclass(slots=True)
class TenantUserSummary:
    user_id: str
    email: str
    full_name: str | None
    user_is_active: bool
    membership_is_active: bool
    is_owner: bool
    role_names: list[str]
    membership_created_at: datetime


@dataclass(slots=True)
class TenantRoleAssignmentBatchResult:
    tenant_id: str
    user_id: str
    is_owner: bool
    role_assignments: list[RoleAssignmentResult] = field(default_factory=list)


@dataclass(slots=True)
class TenantMembershipMutationResult:
    tenant_id: str
    user_id: str
    membership_is_active: bool
    is_owner: bool
    transferred_owner_from_user_id: str | None = None


@dataclass(slots=True)
class TenantMembershipRemovalResult:
    tenant_id: str
    user_id: str
    removed: bool


def _commercial_summary(subscription, *, plan_features: dict[str, object] | None = None) -> TenantOnboardingCommercialSummary | None:
    if not subscription:
        return None

    return TenantOnboardingCommercialSummary(
        id=str(subscription.id),
        plan_code=str(subscription.plan_code),
        plan_name=str(subscription.plan_name),
        commercial_state=str(subscription.commercial_state),
        plan_features=dict(plan_features or {}),
        trial_end_at=subscription.trial_end_at,
        current_period_end_at=subscription.current_period_end_at,
        grace_end_at=subscription.grace_end_at,
        canceled_at=subscription.canceled_at,
    )


def _next_onboarding_action(missing_steps: list[str], warnings: list[str]) -> str:
    if "tenant_not_active" in missing_steps:
        return "activate_tenant"
    if "first_admin_missing" in missing_steps:
        return "create_first_admin"
    if "commercial_subscription_missing" in missing_steps:
        return "start_commercial_trial"
    if "commercial_suspended" in missing_steps or "commercial_canceled" in missing_steps:
        return "reactivate_subscription"
    if warnings:
        return "review_billing"
    return "ready"


async def _tenant_column_exists(session: AsyncSession, column_name: str) -> bool:
    result = await session.execute(
        text(
            """
            select exists (
                select 1
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = 'tenants'
                  and column_name = :column_name
            ) as column_exists
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


async def _tenant_columns_available(
    session: AsyncSession,
    column_names: tuple[str, ...],
) -> set[str]:
    available_columns: set[str] = set()
    for column_name in column_names:
        if await _tenant_column_exists(session, column_name):
            available_columns.add(column_name)
    return available_columns


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_currency_code(
    value: str | None,
    *,
    field_label: str,
    required: bool = False,
) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field_label} is required")
        return None

    normalized = value.strip().upper()
    if not normalized:
        if required:
            raise ValueError(f"{field_label} is required")
        return None

    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError(f"{field_label} must be a valid ISO 4217 3-letter code")

    return normalized


def _normalize_hex_color(
    value: str | None,
    *,
    field_label: str,
) -> str | None:
    cleaned = _clean_optional(value)
    if cleaned is None:
        return None

    normalized = cleaned.upper()
    if not HEX_COLOR_PATTERN.fullmatch(normalized):
        raise ValueError(f"{field_label} must be a valid hex color in #RRGGBB format")

    return normalized


def _normalize_exchange_rate(value: Decimal | str | float | int | None) -> Decimal | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        normalized = value
    else:
        try:
            normalized = Decimal(str(value).strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Secondary currency rate must be a valid decimal value") from exc

    if normalized <= 0:
        raise ValueError("Secondary currency rate must be greater than zero")

    return normalized.quantize(Decimal("0.000001"))


async def bootstrap_tenant(
    session: AsyncSession,
    tenant_id: str,
    tenant_name: str,
    admin_email: str,
    admin_full_name: str | None,
    admin_password: str | None,
    plan_code: str = "starter",
    provider: str = "stripe",
    start_trial: bool = True,
) -> TenantBootstrapResult:
    tenant = await ensure_tenant(
        session,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
    )

    await set_tenant_guc(session, tenant_id)
    try:
        rbac = await seed_default_rbac(session, tenant_id=tenant_id)
        admin = await provision_tenant_user(
            session,
            tenant_id=tenant_id,
            email=admin_email,
            full_name=admin_full_name,
            password=admin_password,
            role_names=("owner", "admin"),
            is_owner=True,
            role_ids_by_name=rbac.role_ids_by_name,
        )
        await ensure_default_plan(session)
        if plan_code != "starter":
            await ensure_plan_catalog(session)
        await bootstrap_tenant_subscription(
            session,
            tenant_id=tenant_id,
            plan_code=plan_code,
            provider=provider,
            start_trial=start_trial,
            customer_email=admin_email,
            customer_name=admin_full_name,
            metadata={"bootstrapped": True},
        )
    finally:
        await reset_tenant_guc(session)

    return TenantBootstrapResult(tenant=tenant, rbac=rbac, admin=admin)


async def ensure_tenant(
    session: AsyncSession,
    tenant_id: str,
    tenant_name: str,
) -> TenantProvisionResult:
    existing_tenant = await _tenant_exists(session, tenant_id=tenant_id)

    await session.execute(
        text(
            """
            insert into public.tenants (id, name, is_active, status, status_reason)
            values (
                cast(:tenant_id as varchar),
                cast(:tenant_name as varchar),
                true,
                'active',
                null
            )
            on conflict (id) do update
              set name = excluded.name,
                  is_active = true,
                  status = 'active',
                  status_reason = null,
                  updated_at = now()
            """
        ),
        {"tenant_id": tenant_id, "tenant_name": tenant_name},
    )

    return TenantProvisionResult(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        created_tenant=not existing_tenant,
    )


async def get_tenant_details(session: AsyncSession, tenant_id: str) -> TenantDetails | None:
    available_columns = await _tenant_columns_available(session, TENANT_OPTIONAL_DETAIL_COLUMNS)
    select_columns = [
        "id",
        "name",
        "is_active",
        "status",
        "status_reason",
        *[column for column in TENANT_OPTIONAL_DETAIL_COLUMNS if column in available_columns],
        "created_at",
        "updated_at",
    ]

    result = await session.execute(
        text(
            f"""
            select {", ".join(select_columns)}
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        return None

    return TenantDetails(
        id=str(row["id"]),
        name=str(row["name"]),
        is_active=bool(row["is_active"]),
        status=str(row["status"]),
        status_reason=row["status_reason"],
        legal_name=row.get("legal_name"),
        address_line_1=row.get("address_line_1"),
        address_line_2=row.get("address_line_2"),
        city=row.get("city"),
        state_region=row.get("state_region"),
        postal_code=row.get("postal_code"),
        country=row.get("country"),
        vat_number=row.get("vat_number"),
        default_currency=(
            str(row["default_currency"]).upper()
            if row.get("default_currency")
            else "USD"
        ),
        secondary_currency=(
            str(row["secondary_currency"]).upper()
            if row.get("secondary_currency")
            else None
        ),
        secondary_currency_rate=(
            Decimal(str(row["secondary_currency_rate"]))
            if row.get("secondary_currency_rate") is not None
            else None
        ),
        secondary_currency_rate_source=(
            str(row["secondary_currency_rate_source"])
            if row.get("secondary_currency_rate_source")
            else None
        ),
        secondary_currency_rate_as_of=row.get("secondary_currency_rate_as_of"),
        brand_primary_color=row.get("brand_primary_color"),
        brand_secondary_color=row.get("brand_secondary_color"),
        sidebar_background_color=row.get("sidebar_background_color"),
        sidebar_text_color=row.get("sidebar_text_color"),
        logo_file_key=row.get("logo_file_key"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_tenant_branding(session: AsyncSession, tenant_id: str) -> TenantBrandingDetails | None:
    available_columns = await _tenant_columns_available(session, TENANT_BRANDING_COLUMNS)
    if "logo_file_key" not in available_columns:
        return TenantBrandingDetails(
            tenant_id=tenant_id,
            logo_file_key=None,
            logo_url=None,
            brand_primary_color=None,
            brand_secondary_color=None,
            sidebar_background_color=None,
            sidebar_text_color=None,
        )

    select_columns = ["id", *[column for column in TENANT_BRANDING_COLUMNS if column in available_columns]]
    result = await session.execute(
        text(
            f"""
            select {", ".join(select_columns)}
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    row = result.mappings().first()
    if not row:
        return None

    logo_file_key = row["logo_file_key"]
    logo_url = None
    if logo_file_key:
        try:
            logo_url = presign_download_url(str(logo_file_key))
        except Exception:
            logo_url = None

    return TenantBrandingDetails(
        tenant_id=str(row["id"]),
        logo_file_key=logo_file_key,
        logo_url=logo_url,
        brand_primary_color=row.get("brand_primary_color"),
        brand_secondary_color=row.get("brand_secondary_color"),
        sidebar_background_color=row.get("sidebar_background_color"),
        sidebar_text_color=row.get("sidebar_text_color"),
    )


async def update_tenant_branding_logo(
    session: AsyncSession,
    *,
    tenant_id: str,
    logo_file_key: str | None,
) -> TenantBrandingDetails | None:
    if not await _tenant_column_exists(session, "logo_file_key"):
        if logo_file_key:
            raise ValueError(
                "Tenant branding requires the latest database migration. "
                "Run alembic upgrade head and retry."
            )
        return TenantBrandingDetails(
            tenant_id=tenant_id,
            logo_file_key=None,
            logo_url=None,
            brand_primary_color=None,
            brand_secondary_color=None,
            sidebar_background_color=None,
            sidebar_text_color=None,
        )

    await session.execute(
        text(
            """
            update public.tenants
            set logo_file_key = :logo_file_key,
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "logo_file_key": logo_file_key,
        },
    )
    return await get_tenant_branding(session, tenant_id=tenant_id)


async def update_tenant_details(
    session: AsyncSession,
    tenant_id: str,
    name: str,
    legal_name: str | None = None,
    address_line_1: str | None = None,
    address_line_2: str | None = None,
    city: str | None = None,
    state_region: str | None = None,
    postal_code: str | None = None,
    country: str | None = None,
    vat_number: str | None = None,
    default_currency: str | None = None,
    secondary_currency: str | None = None,
    secondary_currency_rate: Decimal | str | float | int | None = None,
    brand_primary_color: str | None = None,
    brand_secondary_color: str | None = None,
    sidebar_background_color: str | None = None,
    sidebar_text_color: str | None = None,
) -> TenantDetails:
    available_columns = await _tenant_columns_available(session, TENANT_PROFILE_COLUMNS)
    if available_columns != set(TENANT_PROFILE_COLUMNS):
        raise ValueError(
            "Tenant company settings require the latest database migration. "
            "Run alembic upgrade head and retry."
        )

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Company name is required")

    normalized_default_currency = _normalize_currency_code(
        default_currency,
        field_label="Default currency",
        required=True,
    )
    normalized_secondary_currency = _normalize_currency_code(
        secondary_currency,
        field_label="Secondary currency",
        required=False,
    )
    normalized_secondary_currency_rate = _normalize_exchange_rate(secondary_currency_rate)
    normalized_brand_primary_color = _normalize_hex_color(
        brand_primary_color,
        field_label="Brand primary color",
    )
    normalized_brand_secondary_color = _normalize_hex_color(
        brand_secondary_color,
        field_label="Brand secondary color",
    )
    normalized_sidebar_background_color = _normalize_hex_color(
        sidebar_background_color,
        field_label="Sidebar background color",
    )
    normalized_sidebar_text_color = _normalize_hex_color(
        sidebar_text_color,
        field_label="Sidebar text color",
    )
    if (
        normalized_secondary_currency is not None
        and normalized_secondary_currency == normalized_default_currency
    ):
        raise ValueError("Secondary currency must differ from the default currency")
    if normalized_secondary_currency is None and normalized_secondary_currency_rate is not None:
        raise ValueError("Secondary currency rate requires a configured secondary currency")

    effective_rate_source = "operator_manual" if normalized_secondary_currency_rate is not None else None
    effective_rate_as_of = datetime.now(timezone.utc) if normalized_secondary_currency_rate is not None else None

    result = await session.execute(
        text(
            """
            update public.tenants
            set name = cast(:name as varchar),
                legal_name = cast(:legal_name as varchar),
                address_line_1 = cast(:address_line_1 as varchar),
                address_line_2 = cast(:address_line_2 as varchar),
                city = cast(:city as varchar),
                state_region = cast(:state_region as varchar),
                postal_code = cast(:postal_code as varchar),
                country = cast(:country as varchar),
                vat_number = cast(:vat_number as varchar),
                default_currency = cast(:default_currency as varchar),
                secondary_currency = cast(:secondary_currency as varchar),
                secondary_currency_rate = :secondary_currency_rate,
                secondary_currency_rate_source = cast(:secondary_currency_rate_source as varchar),
                secondary_currency_rate_as_of = :secondary_currency_rate_as_of,
                brand_primary_color = cast(:brand_primary_color as varchar),
                brand_secondary_color = cast(:brand_secondary_color as varchar),
                sidebar_background_color = cast(:sidebar_background_color as varchar),
                sidebar_text_color = cast(:sidebar_text_color as varchar),
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            returning
                id,
                name,
                is_active,
                status,
                status_reason,
                legal_name,
                address_line_1,
                address_line_2,
                city,
                state_region,
                postal_code,
                country,
                vat_number,
                default_currency,
                secondary_currency,
                secondary_currency_rate,
                secondary_currency_rate_source,
                secondary_currency_rate_as_of,
                brand_primary_color,
                brand_secondary_color,
                sidebar_background_color,
                sidebar_text_color,
                logo_file_key,
                created_at,
                updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "name": normalized_name,
            "legal_name": _clean_optional(legal_name),
            "address_line_1": _clean_optional(address_line_1),
            "address_line_2": _clean_optional(address_line_2),
            "city": _clean_optional(city),
            "state_region": _clean_optional(state_region),
            "postal_code": _clean_optional(postal_code),
            "country": _clean_optional(country),
            "vat_number": _clean_optional(vat_number),
            "default_currency": normalized_default_currency,
            "secondary_currency": normalized_secondary_currency,
            "secondary_currency_rate": normalized_secondary_currency_rate,
            "secondary_currency_rate_source": effective_rate_source,
            "secondary_currency_rate_as_of": effective_rate_as_of,
            "brand_primary_color": normalized_brand_primary_color,
            "brand_secondary_color": normalized_brand_secondary_color,
            "sidebar_background_color": normalized_sidebar_background_color,
            "sidebar_text_color": normalized_sidebar_text_color,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    await auth_cache.invalidate_snapshots_for_tenant(tenant_id)

    return TenantDetails(
        id=str(row["id"]),
        name=str(row["name"]),
        is_active=bool(row["is_active"]),
        status=str(row["status"]),
        status_reason=row["status_reason"],
        legal_name=row.get("legal_name"),
        address_line_1=row.get("address_line_1"),
        address_line_2=row.get("address_line_2"),
        city=row.get("city"),
        state_region=row.get("state_region"),
        postal_code=row.get("postal_code"),
        country=row.get("country"),
        vat_number=row.get("vat_number"),
        default_currency=(
            str(row["default_currency"]).upper()
            if row.get("default_currency")
            else normalized_default_currency
        ),
        secondary_currency=(
            str(row["secondary_currency"]).upper()
            if row.get("secondary_currency")
            else normalized_secondary_currency
        ),
        secondary_currency_rate=(
            Decimal(str(row["secondary_currency_rate"]))
            if row.get("secondary_currency_rate") is not None
            else normalized_secondary_currency_rate
        ),
        secondary_currency_rate_source=(
            str(row["secondary_currency_rate_source"])
            if row.get("secondary_currency_rate_source")
            else effective_rate_source
        ),
        secondary_currency_rate_as_of=row.get("secondary_currency_rate_as_of") or effective_rate_as_of,
        brand_primary_color=row.get("brand_primary_color") or normalized_brand_primary_color,
        brand_secondary_color=row.get("brand_secondary_color") or normalized_brand_secondary_color,
        sidebar_background_color=row.get("sidebar_background_color") or normalized_sidebar_background_color,
        sidebar_text_color=row.get("sidebar_text_color") or normalized_sidebar_text_color,
        logo_file_key=row.get("logo_file_key"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _status_to_is_active(status: str) -> bool:
    normalized = status.strip().lower()
    if normalized == "active":
        return True
    if normalized in {"suspended", "disabled"}:
        return False
    raise ValueError(f"Unsupported tenant status: {status}")


async def update_tenant_status(
    session: AsyncSession,
    tenant_id: str,
    status: str,
    status_reason: str | None,
) -> TenantDetails:
    normalized_status = status.strip().lower()
    effective_reason = status_reason.strip() if status_reason else None
    effective_is_active = _status_to_is_active(normalized_status)

    result = await session.execute(
        text(
            """
            update public.tenants
            set status = cast(:status as varchar),
                status_reason = cast(:status_reason as varchar),
                is_active = :is_active,
                updated_at = now()
            where id = cast(:tenant_id as varchar)
            returning id, name, is_active, status, status_reason, created_at, updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "status": normalized_status,
            "status_reason": effective_reason,
            "is_active": effective_is_active,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    await auth_cache.invalidate_snapshots_for_tenant(tenant_id)

    tenant = await get_tenant_details(session, tenant_id=tenant_id)
    if tenant is None:
        raise ValueError(f"Tenant does not exist: {tenant_id}")
    return tenant


async def get_tenant_onboarding_summary(session: AsyncSession, tenant_id: str) -> TenantOnboardingSummary:
    tenant = await get_tenant_details(session, tenant_id)
    if not tenant:
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    users = await list_tenant_users(session, tenant_id)
    subscription = await commercial_service.get_subscription_by_tenant(session, tenant_id=tenant_id)
    plan_features: dict[str, object] = {}
    if subscription:
        plan = await commercial_service.get_plan_by_id(session, plan_id=subscription.plan_id)
        plan_features = dict(plan.features if plan else {})

    owner_count = sum(1 for user in users if user.user_is_active and user.membership_is_active and user.is_owner)
    admin_count = sum(
        1
        for user in users
        if user.user_is_active
        and user.membership_is_active
        and (user.is_owner or "admin" in user.role_names)
    )

    missing_steps: list[str] = []
    warnings: list[str] = []

    if not tenant.is_active:
        missing_steps.append("tenant_not_active")
    if owner_count < 1:
        missing_steps.append("first_admin_missing")
    if not subscription:
        missing_steps.append("commercial_subscription_missing")
    elif subscription.commercial_state in {"suspended", "canceled"}:
        missing_steps.append(f"commercial_{subscription.commercial_state}")
    elif subscription.commercial_state in {"past_due", "grace"}:
        warnings.append("billing_attention_required")

    bootstrap_complete = not missing_steps
    ready_for_use = (
        tenant.is_active
        and owner_count > 0
        and subscription is not None
        and subscription.commercial_state not in {"suspended", "canceled"}
    )

    return TenantOnboardingSummary(
        tenant=tenant,
        commercial_subscription=_commercial_summary(subscription, plan_features=plan_features),
        users_total=len(users),
        owner_count=owner_count,
        admin_count=admin_count,
        bootstrap_complete=bootstrap_complete,
        ready_for_use=ready_for_use,
        missing_steps=missing_steps,
        warnings=warnings,
        next_action=_next_onboarding_action(missing_steps, warnings),
    )


async def list_tenant_roles(session: AsyncSession, tenant_id: str) -> list[TenantRoleSummary]:
    result = await session.execute(
        text(
            """
            select
                r.id,
                r.name,
                r.created_at,
                coalesce(
                    array_agg(distinct p.code) filter (where p.code is not null),
                    '{}'
                ) as permission_codes
            from public.roles r
            left join public.role_permissions rp
              on rp.role_id = r.id
            left join public.permissions p
              on p.id = rp.permission_id
            where r.tenant_id = cast(:tenant_id as varchar)
            group by r.id, r.name, r.created_at
            order by r.name
            """
        ),
        {"tenant_id": tenant_id},
    )

    roles: list[TenantRoleSummary] = []
    for row in result.mappings():
        roles.append(
            TenantRoleSummary(
                id=str(row["id"]),
                name=str(row["name"]),
                permission_codes=list(row["permission_codes"] or []),
                created_at=row["created_at"],
            )
        )
    return roles


async def list_tenant_users(session: AsyncSession, tenant_id: str) -> list[TenantUserSummary]:
    result = await session.execute(
        text(
            """
            select
                u.id as user_id,
                u.email,
                u.full_name,
                u.is_active as user_is_active,
                tu.is_active as membership_is_active,
                tu.is_owner,
                tu.created_at as membership_created_at,
                coalesce(
                    array_agg(distinct r.name) filter (where r.name is not null),
                    '{}'
                ) as role_names
            from public.tenant_users tu
            join public.users u
              on u.id = tu.user_id
            left join public.tenant_user_roles tur
              on tur.tenant_id = tu.tenant_id
             and tur.user_id = tu.user_id
            left join public.roles r
              on r.id = tur.role_id
             and r.tenant_id = tu.tenant_id
            where tu.tenant_id = cast(:tenant_id as varchar)
            group by
                u.id,
                u.email,
                u.full_name,
                u.is_active,
                tu.is_active,
                tu.is_owner,
                tu.created_at
            order by tu.is_owner desc, u.email asc
            """
        ),
        {"tenant_id": tenant_id},
    )

    users: list[TenantUserSummary] = []
    for row in result.mappings():
        users.append(
            TenantUserSummary(
                user_id=str(row["user_id"]),
                email=str(row["email"]),
                full_name=row["full_name"],
                user_is_active=bool(row["user_is_active"]),
                membership_is_active=bool(row["membership_is_active"]),
                is_owner=bool(row["is_owner"]),
                role_names=list(row["role_names"] or []),
                membership_created_at=row["membership_created_at"],
            )
        )
    return users


async def update_tenant_membership(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    membership_is_active: bool | None = None,
    is_owner: bool | None = None,
    transfer_owner_from_user_id: str | None = None,
) -> TenantMembershipMutationResult:
    if membership_is_active is None and is_owner is None and not transfer_owner_from_user_id:
        raise ValueError("Membership change requires at least one update field.")

    users = await list_tenant_users(session, tenant_id)
    target = _find_tenant_user_summary(users, user_id)
    if target is None:
        raise ValueError(f"User is not a member of tenant {tenant_id}: {user_id}")

    next_membership_is_active = (
        target.membership_is_active if membership_is_active is None else membership_is_active
    )
    next_is_owner = target.is_owner if is_owner is None else is_owner

    transfer_source = None
    if transfer_owner_from_user_id:
        if user_id == transfer_owner_from_user_id:
            raise ValueError("Ownership transfer source must differ from the target member.")
        if is_owner is not True:
            raise ValueError("Ownership transfer requires is_owner=true for the target member.")

        transfer_source = _find_tenant_user_summary(users, transfer_owner_from_user_id)
        if transfer_source is None:
            raise ValueError(
                f"Transfer source user is not a member of tenant {tenant_id}: {transfer_owner_from_user_id}"
            )
        if not transfer_source.is_owner:
            raise ValueError(
                f"Transfer source user is not currently an owner for tenant {tenant_id}: {transfer_owner_from_user_id}"
            )

    if (
        not target.is_owner
        and next_is_owner
        and (not target.user_is_active or not next_membership_is_active)
    ):
        raise ValueError("Owner access can only be granted to an active tenant member.")

    simulated_users = _copy_tenant_user_summaries(users)
    simulated_target = _find_tenant_user_summary(simulated_users, user_id)
    assert simulated_target is not None

    simulated_target.membership_is_active = next_membership_is_active
    simulated_target.is_owner = next_is_owner

    simulated_transfer_source = None
    if transfer_source is not None:
        simulated_transfer_source = _find_tenant_user_summary(
            simulated_users,
            transfer_source.user_id,
        )
        assert simulated_transfer_source is not None
        simulated_transfer_source.is_owner = False

    if _is_active_owner(target) and not _is_active_owner(simulated_target):
        if _count_active_owners(simulated_users) == 0:
            if membership_is_active is False:
                raise ValueError(f"Cannot deactivate the last active owner for tenant {tenant_id}.")
            raise ValueError(f"Cannot revoke owner access from the last active owner for tenant {tenant_id}.")

    if (
        transfer_source is not None
        and simulated_transfer_source is not None
        and _is_active_owner(transfer_source)
        and not _is_active_owner(simulated_transfer_source)
        and _count_active_owners(simulated_users) == 0
    ):
        raise ValueError(f"Cannot transfer ownership away from the last active owner for tenant {tenant_id}.")

    if _count_active_admins(users) > 0 and _count_active_admins(simulated_users) == 0:
        raise ValueError(f"Cannot orphan tenant admin access for tenant {tenant_id}.")

    if membership_is_active is not None:
        await session.execute(
            text(
                """
                update public.tenant_users
                set is_active = :is_active
                where tenant_id = cast(:tenant_id as varchar)
                  and user_id = cast(:user_id as varchar)
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "is_active": membership_is_active,
            },
        )

    if is_owner is not None:
        await session.execute(
            text(
                """
                update public.tenant_users
                set is_owner = :is_owner
                where tenant_id = cast(:tenant_id as varchar)
                  and user_id = cast(:user_id as varchar)
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "is_owner": is_owner,
            },
        )

    if transfer_source is not None:
        await _set_membership_owner_state(
            session,
            tenant_id=tenant_id,
            user_id=transfer_source.user_id,
            is_owner=False,
        )

    if next_is_owner:
        await _ensure_role_assignment_by_name(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            role_name="owner",
        )
    elif target.is_owner and not next_is_owner:
        await _remove_role_assignment_by_name(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            role_name="owner",
        )

    if transfer_source is not None:
        await _remove_role_assignment_by_name(
            session,
            tenant_id=tenant_id,
            user_id=transfer_source.user_id,
            role_name="owner",
        )

    await auth_cache.invalidate_snapshots_for_tenant(tenant_id)

    return TenantMembershipMutationResult(
        tenant_id=tenant_id,
        user_id=user_id,
        membership_is_active=simulated_target.membership_is_active,
        is_owner=simulated_target.is_owner,
        transferred_owner_from_user_id=(
            transfer_source.user_id if transfer_source is not None else None
        ),
    )


async def remove_tenant_membership(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
) -> TenantMembershipRemovalResult:
    users = await list_tenant_users(session, tenant_id)
    target = _find_tenant_user_summary(users, user_id)
    if target is None:
        raise ValueError(f"User is not a member of tenant {tenant_id}: {user_id}")

    simulated_users = [
        user
        for user in _copy_tenant_user_summaries(users)
        if user.user_id != user_id
    ]

    if _is_active_owner(target) and _count_active_owners(simulated_users) == 0:
        raise ValueError(f"Cannot remove the last active owner for tenant {tenant_id}.")

    if _count_active_admins(users) > 0 and _count_active_admins(simulated_users) == 0:
        raise ValueError(f"Cannot orphan tenant admin access for tenant {tenant_id}.")

    await session.execute(
        text(
            """
            delete from public.tenant_user_roles
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    await session.execute(
        text(
            """
            delete from public.tenant_users
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )

    await auth_cache.invalidate_snapshots_for_tenant(tenant_id)

    return TenantMembershipRemovalResult(
        tenant_id=tenant_id,
        user_id=user_id,
        removed=True,
    )


async def provision_tenant_user(
    session: AsyncSession,
    tenant_id: str,
    email: str,
    full_name: str | None,
    password: str | None,
    role_names: tuple[str, ...] | list[str] = ("user",),
    is_owner: bool = False,
    role_ids_by_name: dict[str, str] | None = None,
) -> TenantUserProvisionResult:
    if not await _tenant_exists(session, tenant_id=tenant_id):
        raise ValueError(f"Tenant does not exist: {tenant_id}")

    normalized_role_names = _normalize_role_names(role_names)
    if is_owner and "owner" not in normalized_role_names:
        normalized_role_names.append("owner")
    if not normalized_role_names:
        raise ValueError("At least one role name must be provided")

    resolved_role_ids = role_ids_by_name or await _load_role_ids_by_name(
        session,
        tenant_id=tenant_id,
        role_names=normalized_role_names,
    )

    user = await provision_user(
        session,
        email=email,
        full_name=full_name,
        password=password,
    )
    membership = await ensure_tenant_membership(
        session,
        tenant_id=tenant_id,
        user_id=user.user_id,
        is_owner=is_owner or ("owner" in normalized_role_names),
    )

    role_assignments: list[RoleAssignmentResult] = []
    for role_name in normalized_role_names:
        role_id = resolved_role_ids.get(role_name)
        if not role_id:
            raise ValueError(f"Role is not seeded for tenant {tenant_id}: {role_name}")

        assignment = await ensure_tenant_user_role(
            session,
            tenant_id=tenant_id,
            user_id=user.user_id,
            role_id=role_id,
            role_name=role_name,
        )
        role_assignments.append(assignment)

    return TenantUserProvisionResult(
        tenant_id=tenant_id,
        user=user,
        membership=membership,
        role_assignments=role_assignments,
    )


async def provision_tenant_admin(
    session: AsyncSession,
    tenant_id: str,
    admin_email: str,
    admin_full_name: str | None,
    admin_password: str | None,
    role_names: tuple[str, ...] = ("admin",),
    is_owner: bool = False,
    seeded_rbac: RbacSeedResult | None = None,
) -> AdminProvisionResult:
    return await provision_tenant_user(
        session,
        tenant_id=tenant_id,
        email=admin_email,
        full_name=admin_full_name,
        password=admin_password,
        role_names=role_names,
        is_owner=is_owner,
        role_ids_by_name=(seeded_rbac.role_ids_by_name if seeded_rbac else None),
    )


async def assign_roles_to_tenant_user(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    role_names: tuple[str, ...] | list[str],
    is_owner: bool = False,
) -> TenantRoleAssignmentBatchResult:
    normalized_role_names = _normalize_role_names(role_names)
    if not normalized_role_names:
        raise ValueError("At least one role name must be provided")

    existing_owner_state = await _get_membership_owner_state(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if existing_owner_state is None:
        raise ValueError(f"User is not a member of tenant {tenant_id}: {user_id}")

    promote_owner = is_owner or ("owner" in normalized_role_names)
    membership = await ensure_tenant_membership(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        is_owner=promote_owner,
    )
    resolved_role_ids = await _load_role_ids_by_name(
        session,
        tenant_id=tenant_id,
        role_names=normalized_role_names,
    )

    role_assignments: list[RoleAssignmentResult] = []
    for role_name in normalized_role_names:
        assignment = await ensure_tenant_user_role(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=resolved_role_ids[role_name],
            role_name=role_name,
        )
        role_assignments.append(assignment)

    return TenantRoleAssignmentBatchResult(
        tenant_id=tenant_id,
        user_id=user_id,
        is_owner=membership.is_owner,
        role_assignments=role_assignments,
    )


async def ensure_tenant_membership(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    is_owner: bool,
) -> MembershipProvisionResult:
    existing_owner_state = await _get_membership_owner_state(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
    )
    membership_exists = existing_owner_state is not None

    await session.execute(
        text(
            """
            insert into public.tenant_users (tenant_id, user_id, is_owner, is_active)
            values (
                cast(:tenant_id as varchar),
                cast(:user_id as varchar),
                :is_owner,
                true
            )
            on conflict (tenant_id, user_id) do update
              set is_owner = public.tenant_users.is_owner or excluded.is_owner,
                  is_active = true
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "is_owner": is_owner},
    )

    effective_is_owner = bool(existing_owner_state) or is_owner

    return MembershipProvisionResult(
        tenant_id=tenant_id,
        user_id=user_id,
        created_membership=not membership_exists,
        is_owner=effective_is_owner,
    )


async def ensure_tenant_user_role(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    role_id: str,
    role_name: str,
) -> RoleAssignmentResult:
    assignment_exists = await _tenant_user_role_exists(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
    )

    await session.execute(
        text(
            """
            insert into public.tenant_user_roles (tenant_id, user_id, role_id)
            values (
                cast(:tenant_id as varchar),
                cast(:user_id as varchar),
                cast(:role_id as varchar)
            )
            on conflict do nothing
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "role_id": role_id},
    )

    return RoleAssignmentResult(
        role_name=role_name,
        role_id=role_id,
        created_assignment=not assignment_exists,
    )


async def _set_membership_owner_state(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    is_owner: bool,
) -> None:
    await session.execute(
        text(
            """
            update public.tenant_users
            set is_owner = :is_owner
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "is_owner": is_owner},
    )


async def _ensure_role_assignment_by_name(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    role_name: str,
) -> RoleAssignmentResult:
    role_id = (await _load_role_ids_by_name(session, tenant_id, [role_name]))[role_name]
    return await ensure_tenant_user_role(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
        role_name=role_name,
    )


async def _remove_role_assignment_by_name(
    session: AsyncSession,
    *,
    tenant_id: str,
    user_id: str,
    role_name: str,
) -> None:
    role_id = (await _load_role_ids_by_name(session, tenant_id, [role_name]))[role_name]
    await session.execute(
        text(
            """
            delete from public.tenant_user_roles
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
              and role_id = cast(:role_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role_id": role_id,
        },
    )


async def _tenant_exists(session: AsyncSession, tenant_id: str) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.tenants
            where id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    return result.scalar_one_or_none() is not None


async def _get_membership_owner_state(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> bool | None:
    result = await session.execute(
        text(
            """
            select is_owner
            from public.tenant_users
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id},
    )
    state = result.scalar_one_or_none()
    if state is None:
        return None
    return bool(state)


async def _tenant_user_role_exists(
    session: AsyncSession,
    tenant_id: str,
    user_id: str,
    role_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.tenant_user_roles
            where tenant_id = cast(:tenant_id as varchar)
              and user_id = cast(:user_id as varchar)
              and role_id = cast(:role_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "role_id": role_id},
    )
    return result.scalar_one_or_none() is not None


async def _load_role_ids_by_name(
    session: AsyncSession,
    tenant_id: str,
    role_names: list[str],
) -> dict[str, str]:
    if not role_names:
        return {}

    result = await session.execute(
        text(
            """
            select id, name
            from public.roles
            where tenant_id = cast(:tenant_id as varchar)
            """
        ),
        {"tenant_id": tenant_id},
    )
    role_ids_by_name = {
        str(row.name): str(row.id)
        for row in result
        if str(row.name) in role_names
    }
    missing_role_names = [role_name for role_name in role_names if role_name not in role_ids_by_name]
    if missing_role_names:
        raise ValueError(
            f"Roles not found for tenant {tenant_id}: {', '.join(missing_role_names)}"
        )
    return role_ids_by_name


def _normalize_role_names(role_names: tuple[str, ...] | list[str]) -> list[str]:
    normalized: list[str] = []
    for role_name in role_names:
        cleaned = role_name.strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _find_tenant_user_summary(
    users: list[TenantUserSummary],
    user_id: str,
) -> TenantUserSummary | None:
    for user in users:
        if user.user_id == user_id:
            return user
    return None


def _copy_tenant_user_summaries(
    users: list[TenantUserSummary],
) -> list[TenantUserSummary]:
    return [
        TenantUserSummary(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            user_is_active=user.user_is_active,
            membership_is_active=user.membership_is_active,
            is_owner=user.is_owner,
            role_names=list(user.role_names),
            membership_created_at=user.membership_created_at,
        )
        for user in users
    ]


def _is_active_owner(user: TenantUserSummary) -> bool:
    return user.user_is_active and user.membership_is_active and user.is_owner


def _has_active_admin_access(user: TenantUserSummary) -> bool:
    return (
        user.user_is_active
        and user.membership_is_active
        and (user.is_owner or "admin" in user.role_names)
    )


def _count_active_owners(users: list[TenantUserSummary]) -> int:
    return sum(1 for user in users if _is_active_owner(user))


def _count_active_admins(users: list[TenantUserSummary]) -> int:
    return sum(1 for user in users if _has_active_admin_access(user))
