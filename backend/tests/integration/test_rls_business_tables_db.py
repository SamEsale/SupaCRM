from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from dotenv import load_dotenv

asyncpg = pytest.importorskip(
    "asyncpg", reason="Install asyncpg to run DB-backed RLS verification tests"
)

TARGET_TABLES: tuple[str, ...] = (
    "companies",
    "contacts",
    "deals",
    "quotes",
    "invoices",
)

TENANT_A = "rls-test-tenant-a"
TENANT_B = "rls-test-tenant-b"
APP_DSN_FALLBACK = "postgresql://supacrm_app:supacrm_app@127.0.0.1:5432/supacrm"


@dataclass(frozen=True)
class DbConnections:
    admin: asyncpg.Connection
    app: asyncpg.Connection


def _find_upwards(filename: str, start: Path) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / filename
        if candidate.exists():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _load_env_supa_if_present() -> None:
    env_path = _find_upwards(".env.supa", Path.cwd())
    if env_path:
        load_dotenv(env_path, override=False)


def _normalize_asyncpg_dsn(dsn: str | None) -> str | None:
    if not dsn:
        return None
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if dsn.startswith("postgresql+psycopg://"):
        return dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn


def _get_admin_dsn() -> str | None:
    return _normalize_asyncpg_dsn(
        os.getenv("DATABASE_URL_ADMIN_ASYNC")
        or os.getenv("DATABASE_URL_ADMIN_SYNC")
        or os.getenv("DATABASE_URL_SYNC")
        or os.getenv("DATABASE_URL_ASYNC")
        or os.getenv("DATABASE_URL")
    )


def _get_app_dsn() -> str | None:
    return _normalize_asyncpg_dsn(os.getenv("APP_USER_DSN")) or APP_DSN_FALLBACK


def _rows_affected(command_tag: str) -> int:
    parts = command_tag.strip().split()
    last = parts[-1] if parts else ""
    if not last.isdigit():
        raise AssertionError(
            f"Unable to parse rows affected from command tag: {command_tag}"
        )
    return int(last)


def _assert_rls_denied(exc: BaseException) -> None:
    message = str(exc).lower()
    sqlstate = getattr(exc, "sqlstate", None)
    if sqlstate == "42501":
        return
    if "row-level security" in message:
        return
    if "violates row-level security policy" in message:
        return
    raise AssertionError(
        f"Expected RLS denial, got: {type(exc).__name__}: {exc}"
    ) from exc


async def _set_tenant(conn: asyncpg.Connection, tenant_id: str) -> None:
    await conn.execute("select set_config('app.tenant_id', $1, true)", tenant_id)


async def _ensure_tenant(admin: asyncpg.Connection, tenant_id: str, name: str) -> None:
    await admin.execute(
        """
        insert into public.tenants (id, name, is_active, status)
        values ($1, $2, true, 'active')
        on conflict (id) do update
        set name = excluded.name,
            is_active = true,
            status = 'active',
            updated_at = now()
        """,
        tenant_id,
        name,
    )


@pytest_asyncio.fixture(scope="function")
async def db_connections() -> AsyncIterator[DbConnections]:
    _load_env_supa_if_present()

    admin_dsn = _get_admin_dsn()
    if not admin_dsn:
        pytest.skip(
            "Skipping DB RLS verification: DATABASE_URL_ADMIN_ASYNC / DATABASE_URL_ADMIN_SYNC / "
            "DATABASE_URL_SYNC / DATABASE_URL_ASYNC / DATABASE_URL not set"
        )

    app_dsn = _get_app_dsn()

    try:
        admin = await asyncpg.connect(admin_dsn)
    except Exception as exc:
        pytest.skip(f"Skipping DB RLS verification: cannot connect admin DSN ({exc})")

    try:
        app = await asyncpg.connect(app_dsn)
    except Exception as exc:
        await admin.close()
        pytest.skip(
            "Skipping DB RLS verification: cannot connect app-user DSN "
            f"(APP_USER_DSN={os.getenv('APP_USER_DSN')!r}, fallback={APP_DSN_FALLBACK!r}) ({exc})"
        )

    try:
        await _ensure_tenant(admin, TENANT_A, "RLS Tenant A")
        await _ensure_tenant(admin, TENANT_B, "RLS Tenant B")
        yield DbConnections(admin=admin, app=app)
    finally:
        if not app.is_closed():
            await app.close()
        if not admin.is_closed():
            await admin.close()


@pytest.mark.asyncio
async def test_rls_metadata_present_for_target_tables(
    db_connections: DbConnections,
) -> None:
    rows = await db_connections.admin.fetch(
        """
        select
            c.relname as table_name,
            c.relrowsecurity as rls_enabled,
            c.relforcerowsecurity as rls_forced
        from pg_class c
        join pg_namespace n
          on n.oid = c.relnamespace
        where n.nspname = 'public'
          and c.relname = any($1::text[])
        order by c.relname
        """,
        list(TARGET_TABLES),
    )

    by_table = {row["table_name"]: row for row in rows}
    assert set(by_table.keys()) == set(TARGET_TABLES)

    for table in TARGET_TABLES:
        assert by_table[table]["rls_enabled"] is True
        assert by_table[table]["rls_forced"] is True

        policy_name = f"{table}_tenant_isolation"
        exists = await db_connections.admin.fetchval(
            """
            select exists (
                select 1
                from pg_policy p
                join pg_class c
                  on c.oid = p.polrelid
                join pg_namespace n
                  on n.oid = c.relnamespace
                where n.nspname = 'public'
                  and c.relname = $1
                  and p.polname = $2
            )
            """,
            table,
            policy_name,
        )
        assert exists is True


@pytest.mark.asyncio
async def test_companies_rls_select_insert_update_delete(
    db_connections: DbConnections,
) -> None:
    admin = db_connections.admin
    app = db_connections.app

    company_a = f"cmp_{uuid.uuid4().hex[:12]}"
    company_b = f"cmp_{uuid.uuid4().hex[:12]}"
    company_insert = f"cmp_{uuid.uuid4().hex[:12]}"

    await admin.execute(
        """
        insert into public.companies (id, tenant_id, name, notes)
        values ($1, $2, $3, 'seed-a'),
               ($4, $5, $6, 'seed-b')
        """,
        company_a,
        TENANT_A,
        f"Company A {company_a}",
        company_b,
        TENANT_B,
        f"Company B {company_b}",
    )

    try:
        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            rows = await app.fetch(
                "select id from public.companies where id in ($1, $2) order by id",
                company_a,
                company_b,
            )
            assert [row["id"] for row in rows] == [company_a]

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    """
                    insert into public.companies (id, tenant_id, name, notes)
                    values ($1, $2, $3, 'cross-tenant-insert')
                    """,
                    f"cmp_{uuid.uuid4().hex[:12]}",
                    TENANT_B,
                    "Cross Tenant Company",
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            await app.execute(
                """
                insert into public.companies (id, tenant_id, name, notes)
                values ($1, $2, $3, 'same-tenant-insert')
                """,
                company_insert,
                TENANT_A,
                f"Company Insert {company_insert}",
            )

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            update_cross = await app.execute(
                "update public.companies set notes = 'updated-cross' where id = $1",
                company_b,
            )
            assert _rows_affected(update_cross) == 0

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    "update public.companies set tenant_id = $2 where id = $1",
                    company_a,
                    TENANT_B,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            delete_cross = await app.execute(
                "delete from public.companies where id = $1",
                company_b,
            )
            assert _rows_affected(delete_cross) == 0
    finally:
        await admin.execute(
            "delete from public.companies where id = any($1::varchar[])",
            [company_a, company_b, company_insert],
        )


@pytest.mark.asyncio
async def test_contacts_rls_select_insert_update_delete(
    db_connections: DbConnections,
) -> None:
    admin = db_connections.admin
    app = db_connections.app

    contact_a = f"con_{uuid.uuid4().hex[:12]}"
    contact_b = f"con_{uuid.uuid4().hex[:12]}"
    contact_insert = f"con_{uuid.uuid4().hex[:12]}"

    await admin.execute(
        """
        insert into public.contacts (id, tenant_id, first_name, notes)
        values ($1, $2, 'ContactA', 'seed-a'),
               ($3, $4, 'ContactB', 'seed-b')
        """,
        contact_a,
        TENANT_A,
        contact_b,
        TENANT_B,
    )

    try:
        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            rows = await app.fetch(
                "select id from public.contacts where id in ($1, $2) order by id",
                contact_a,
                contact_b,
            )
            assert [row["id"] for row in rows] == [contact_a]

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    """
                    insert into public.contacts (id, tenant_id, first_name, notes)
                    values ($1, $2, 'CrossContact', 'cross-tenant-insert')
                    """,
                    f"con_{uuid.uuid4().hex[:12]}",
                    TENANT_B,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            await app.execute(
                """
                insert into public.contacts (id, tenant_id, first_name, notes)
                values ($1, $2, 'InsertedContact', 'same-tenant-insert')
                """,
                contact_insert,
                TENANT_A,
            )

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            update_cross = await app.execute(
                "update public.contacts set notes = 'updated-cross' where id = $1",
                contact_b,
            )
            assert _rows_affected(update_cross) == 0

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    "update public.contacts set tenant_id = $2 where id = $1",
                    contact_a,
                    TENANT_B,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            delete_cross = await app.execute(
                "delete from public.contacts where id = $1",
                contact_b,
            )
            assert _rows_affected(delete_cross) == 0
    finally:
        await admin.execute(
            "delete from public.contacts where id = any($1::varchar[])",
            [contact_a, contact_b, contact_insert],
        )


@pytest.mark.asyncio
async def test_deals_rls_select_insert_update_delete(
    db_connections: DbConnections,
) -> None:
    admin = db_connections.admin
    app = db_connections.app

    company_a = f"cmp_{uuid.uuid4().hex[:12]}"
    company_b = f"cmp_{uuid.uuid4().hex[:12]}"
    deal_a = f"deal_{uuid.uuid4().hex[:12]}"
    deal_b = f"deal_{uuid.uuid4().hex[:12]}"
    deal_insert = f"deal_{uuid.uuid4().hex[:12]}"

    await admin.execute(
        """
        insert into public.companies (id, tenant_id, name, notes)
        values ($1, $2, $3, 'seed-deal-a'),
               ($4, $5, $6, 'seed-deal-b')
        """,
        company_a,
        TENANT_A,
        f"Deal Company A {company_a}",
        company_b,
        TENANT_B,
        f"Deal Company B {company_b}",
    )

    await admin.execute(
        """
        insert into public.deals (
            id, tenant_id, name, company_id, amount, currency, stage, status, notes
        )
        values
            ($1, $2, $3, $4, 10.00, 'USD', 'new lead', 'open', 'seed-a'),
            ($5, $6, $7, $8, 20.00, 'USD', 'new lead', 'open', 'seed-b')
        """,
        deal_a,
        TENANT_A,
        f"Deal A {deal_a}",
        company_a,
        deal_b,
        TENANT_B,
        f"Deal B {deal_b}",
        company_b,
    )

    try:
        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            rows = await app.fetch(
                "select id from public.deals where id in ($1, $2) order by id",
                deal_a,
                deal_b,
            )
            assert [row["id"] for row in rows] == [deal_a]

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    """
                    insert into public.deals (
                        id, tenant_id, name, company_id, amount, currency, stage, status, notes
                    )
                    values ($1, $2, $3, $4, 30.00, 'USD', 'new lead', 'open', 'cross-tenant-insert')
                    """,
                    f"deal_{uuid.uuid4().hex[:12]}",
                    TENANT_B,
                    "Cross Deal",
                    company_b,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            await app.execute(
                """
                insert into public.deals (
                    id, tenant_id, name, company_id, amount, currency, stage, status, notes
                )
                values ($1, $2, $3, $4, 40.00, 'USD', 'new lead', 'open', 'same-tenant-insert')
                """,
                deal_insert,
                TENANT_A,
                "Inserted Deal",
                company_a,
            )

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            update_cross = await app.execute(
                "update public.deals set notes = 'updated-cross' where id = $1",
                deal_b,
            )
            assert _rows_affected(update_cross) == 0

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    "update public.deals set tenant_id = $2 where id = $1",
                    deal_a,
                    TENANT_B,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            delete_cross = await app.execute(
                "delete from public.deals where id = $1",
                deal_b,
            )
            assert _rows_affected(delete_cross) == 0
    finally:
        await admin.execute(
            "delete from public.deals where id = any($1::varchar[])",
            [deal_a, deal_b, deal_insert],
        )
        await admin.execute(
            "delete from public.companies where id = any($1::varchar[])",
            [company_a, company_b],
        )


@pytest.mark.asyncio
async def test_quotes_rls_select_insert_update_delete(
    db_connections: DbConnections,
) -> None:
    admin = db_connections.admin
    app = db_connections.app

    company_a = f"cmp_{uuid.uuid4().hex[:12]}"
    company_b = f"cmp_{uuid.uuid4().hex[:12]}"
    quote_a = f"qte_{uuid.uuid4().hex[:12]}"
    quote_b = f"qte_{uuid.uuid4().hex[:12]}"
    quote_insert = f"qte_{uuid.uuid4().hex[:12]}"
    number_a = f"QTE-RLS-A-{uuid.uuid4().hex[:8].upper()}"
    number_b = f"QTE-RLS-B-{uuid.uuid4().hex[:8].upper()}"
    number_insert = f"QTE-RLS-I-{uuid.uuid4().hex[:8].upper()}"

    await admin.execute(
        """
        insert into public.companies (id, tenant_id, name, notes)
        values ($1, $2, $3, 'seed-quote-a'),
               ($4, $5, $6, 'seed-quote-b')
        """,
        company_a,
        TENANT_A,
        f"Quote Company A {company_a}",
        company_b,
        TENANT_B,
        f"Quote Company B {company_b}",
    )

    await admin.execute(
        """
        insert into public.quotes (
            id, tenant_id, number, company_id, issue_date, expiry_date, currency, total_amount, status, notes
        )
        values
            ($1, $2, $3, $4, $5, $6, 'USD', 100.00, 'draft', 'seed-a'),
            ($7, $8, $9, $10, $11, $12, 'USD', 200.00, 'draft', 'seed-b')
        """,
        quote_a,
        TENANT_A,
        number_a,
        company_a,
        date(2026, 1, 1),
        date(2026, 1, 31),
        quote_b,
        TENANT_B,
        number_b,
        company_b,
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    try:
        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            rows = await app.fetch(
                "select id from public.quotes where id in ($1, $2) order by id",
                quote_a,
                quote_b,
            )
            assert [row["id"] for row in rows] == [quote_a]

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    """
                    insert into public.quotes (
                        id, tenant_id, number, company_id, issue_date, expiry_date, currency, total_amount, status, notes
                    )
                    values ($1, $2, $3, $4, $5, $6, 'USD', 300.00, 'draft', 'cross-tenant-insert')
                    """,
                    f"qte_{uuid.uuid4().hex[:12]}",
                    TENANT_B,
                    f"QTE-RLS-X-{uuid.uuid4().hex[:8].upper()}",
                    company_b,
                    date(2026, 2, 1),
                    date(2026, 2, 28),
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            await app.execute(
                """
                insert into public.quotes (
                    id, tenant_id, number, company_id, issue_date, expiry_date, currency, total_amount, status, notes
                )
                values ($1, $2, $3, $4, $5, $6, 'USD', 400.00, 'draft', 'same-tenant-insert')
                """,
                quote_insert,
                TENANT_A,
                number_insert,
                company_a,
                date(2026, 3, 1),
                date(2026, 3, 31),
            )

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            update_cross = await app.execute(
                "update public.quotes set notes = 'updated-cross' where id = $1",
                quote_b,
            )
            assert _rows_affected(update_cross) == 0

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    "update public.quotes set tenant_id = $2 where id = $1",
                    quote_a,
                    TENANT_B,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            delete_cross = await app.execute(
                "delete from public.quotes where id = $1",
                quote_b,
            )
            assert _rows_affected(delete_cross) == 0
    finally:
        await admin.execute(
            "delete from public.quotes where id = any($1::varchar[])",
            [quote_a, quote_b, quote_insert],
        )
        await admin.execute(
            "delete from public.companies where id = any($1::varchar[])",
            [company_a, company_b],
        )


@pytest.mark.asyncio
async def test_invoices_rls_select_insert_update_delete(
    db_connections: DbConnections,
) -> None:
    admin = db_connections.admin
    app = db_connections.app

    company_a = f"cmp_{uuid.uuid4().hex[:12]}"
    company_b = f"cmp_{uuid.uuid4().hex[:12]}"
    invoice_a = f"inv_{uuid.uuid4().hex[:12]}"
    invoice_b = f"inv_{uuid.uuid4().hex[:12]}"
    invoice_insert = f"inv_{uuid.uuid4().hex[:12]}"
    number_a = f"INV-RLS-A-{uuid.uuid4().hex[:8].upper()}"
    number_b = f"INV-RLS-B-{uuid.uuid4().hex[:8].upper()}"
    number_insert = f"INV-RLS-I-{uuid.uuid4().hex[:8].upper()}"

    await admin.execute(
        """
        insert into public.companies (id, tenant_id, name, notes)
        values ($1, $2, $3, 'seed-invoice-a'),
               ($4, $5, $6, 'seed-invoice-b')
        """,
        company_a,
        TENANT_A,
        f"Invoice Company A {company_a}",
        company_b,
        TENANT_B,
        f"Invoice Company B {company_b}",
    )

    await admin.execute(
        """
        insert into public.invoices (
            id, tenant_id, number, company_id, issue_date, due_date, currency, total_amount, status, notes
        )
        values
            ($1, $2, $3, $4, $5, $6, 'USD', 120.00, 'draft', 'seed-a'),
            ($7, $8, $9, $10, $11, $12, 'USD', 220.00, 'draft', 'seed-b')
        """,
        invoice_a,
        TENANT_A,
        number_a,
        company_a,
        date(2026, 1, 1),
        date(2026, 1, 15),
        invoice_b,
        TENANT_B,
        number_b,
        company_b,
        date(2026, 1, 1),
        date(2026, 1, 15),
    )

    try:
        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            rows = await app.fetch(
                "select id from public.invoices where id in ($1, $2) order by id",
                invoice_a,
                invoice_b,
            )
            assert [row["id"] for row in rows] == [invoice_a]

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    """
                    insert into public.invoices (
                        id, tenant_id, number, company_id, issue_date, due_date, currency, total_amount, status, notes
                    )
                    values ($1, $2, $3, $4, $5, $6, 'USD', 320.00, 'draft', 'cross-tenant-insert')
                    """,
                    f"inv_{uuid.uuid4().hex[:12]}",
                    TENANT_B,
                    f"INV-RLS-X-{uuid.uuid4().hex[:8].upper()}",
                    company_b,
                    date(2026, 2, 1),
                    date(2026, 2, 20),
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            await app.execute(
                """
                insert into public.invoices (
                    id, tenant_id, number, company_id, issue_date, due_date, currency, total_amount, status, notes
                )
                values ($1, $2, $3, $4, $5, $6, 'USD', 420.00, 'draft', 'same-tenant-insert')
                """,
                invoice_insert,
                TENANT_A,
                number_insert,
                company_a,
                date(2026, 3, 1),
                date(2026, 3, 20),
            )

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            update_cross = await app.execute(
                "update public.invoices set notes = 'updated-cross' where id = $1",
                invoice_b,
            )
            assert _rows_affected(update_cross) == 0

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            with pytest.raises(asyncpg.PostgresError) as exc:
                await app.execute(
                    "update public.invoices set tenant_id = $2 where id = $1",
                    invoice_a,
                    TENANT_B,
                )
            _assert_rls_denied(exc.value)

        async with app.transaction():
            await _set_tenant(app, TENANT_A)
            delete_cross = await app.execute(
                "delete from public.invoices where id = $1",
                invoice_b,
            )
            assert _rows_affected(delete_cross) == 0
    finally:
        await admin.execute(
            "delete from public.invoices where id = any($1::varchar[])",
            [invoice_a, invoice_b, invoice_insert],
        )
        await admin.execute(
            "delete from public.companies where id = any($1::varchar[])",
            [company_a, company_b],
        )
