from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.crm.service import export_contacts_csv, import_contacts_from_csv


class _FakeMappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class _FakeResult:
    def __init__(self, *, rows: list[dict[str, Any]] | None = None, scalar: Any = None) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one(self) -> Any:
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeCrmImportSession:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.companies: dict[str, dict[str, Any]] = {
            "company-1": {
                "id": "company-1",
                "tenant_id": "tenant-1",
                "name": "Northwind",
                "website": None,
                "email": None,
                "phone": None,
                "industry": None,
                "address": None,
                "vat_number": None,
                "registration_number": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
            },
            "company-2": {
                "id": "company-2",
                "tenant_id": "tenant-2",
                "name": "Outside Tenant",
                "website": None,
                "email": None,
                "phone": None,
                "industry": None,
                "address": None,
                "vat_number": None,
                "registration_number": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
            },
        }
        self.contacts: dict[str, dict[str, Any]] = {
            "contact-existing": {
                "id": "contact-existing",
                "tenant_id": "tenant-1",
                "first_name": "Existing",
                "last_name": "Person",
                "email": "existing@example.com",
                "phone": None,
                "company_id": "company-1",
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
            }
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

        if "select name from public.companies" in sql:
            company = self.companies.get(str(payload["company_id"]))
            if company and company["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(rows=[{"name": company["name"]}])
            return _FakeResult(rows=[])

        if "from public.companies" in sql and "lower(name) = lower(cast(:name as varchar))" in sql:
            for company in self.companies.values():
                if company["tenant_id"] != str(payload["tenant_id"]):
                    continue
                if company["name"].lower() == str(payload["name"]).lower():
                    return _FakeResult(rows=[dict(company)])
            return _FakeResult(rows=[])

        if "insert into public.companies" in sql:
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "name": str(payload["name"]),
                "website": payload.get("website"),
                "email": payload.get("email"),
                "phone": payload.get("phone"),
                "industry": payload.get("industry"),
                "address": payload.get("address"),
                "vat_number": payload.get("vat_number"),
                "registration_number": payload.get("registration_number"),
                "notes": payload.get("notes"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            self.companies[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "insert into public.contacts" in sql:
            email = payload.get("email")
            for contact in self.contacts.values():
                if (
                    contact["tenant_id"] == str(payload["tenant_id"])
                    and contact["email"]
                    and email
                    and str(contact["email"]).lower() == str(email).lower()
                ):
                    raise IntegrityError(
                        statement,
                        params,
                        Exception('duplicate key value violates unique constraint "uq_contacts_tenant_email"'),
                    )

            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "first_name": str(payload["first_name"]),
                "last_name": payload.get("last_name"),
                "email": payload.get("email"),
                "phone": payload.get("phone"),
                "company_id": payload.get("company_id"),
                "company": payload.get("company"),
                "job_title": payload.get("job_title"),
                "notes": payload.get("notes"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            self.contacts[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "from public.contacts" in sql and "lower(coalesce(email, '')) = lower(cast(:email as varchar))" in sql:
            for contact in self.contacts.values():
                if (
                    contact["tenant_id"] == str(payload["tenant_id"])
                    and contact["email"]
                    and str(contact["email"]).lower() == str(payload["email"]).lower()
                ):
                    return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "from public.contacts" in sql and "order by created_at desc, id desc" in sql:
            rows = [
                dict(contact)
                for contact in self.contacts.values()
                if contact["tenant_id"] == str(payload["tenant_id"])
            ]
            search = str(payload.get("search", "")).replace("%", "").lower()
            if search:
                rows = [
                    row
                    for row in rows
                    if search in " ".join(
                        [
                            str(row["first_name"] or ""),
                            str(row["last_name"] or ""),
                            str(row["email"] or ""),
                            str(row["company"] or ""),
                        ]
                    ).lower()
                ]
            company_id = payload.get("company_id")
            if company_id:
                rows = [row for row in rows if row["company_id"] == str(company_id)]
            rows.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
            return _FakeResult(rows=rows)

        raise AssertionError(f"Unhandled SQL in FakeCrmImportSession: {sql}")


@pytest.mark.asyncio
async def test_import_contacts_reports_row_errors_and_keeps_existing_tenant_scope() -> None:
    session = FakeCrmImportSession()

    result = await import_contacts_from_csv(
        session,
        tenant_id="tenant-1",
        csv_text=(
            "first_name,last_name,email,phone,company,job_title,notes\n"
            "Ada,Lovelace,ada@example.com,,Northwind,Engineer,Imported row\n"
            ",Missing First,missing@example.com,,,Operator,\n"
            "Grace,Hopper,existing@example.com,,,Engineer,\n"
            "Casey,External,casey@example.com,,Outside Tenant,,\n"
        ),
        create_missing_companies=False,
    )

    assert result.total_rows == 4
    assert result.imported_rows == 1
    assert result.error_rows == 3
    assert [row.status for row in result.rows] == ["imported", "error", "error", "error"]
    assert "first_name is required" in result.rows[1].message
    assert "already exists for this tenant" in result.rows[2].message
    assert "Company was not found for this tenant" in result.rows[3].message


@pytest.mark.asyncio
async def test_import_contacts_can_create_missing_companies_when_requested() -> None:
    session = FakeCrmImportSession()

    result = await import_contacts_from_csv(
        session,
        tenant_id="tenant-1",
        csv_text=(
            "first_name,last_name,email,phone,company,job_title,notes\n"
            "Jamie,Rowe,jamie@example.com,,Fresh Company,Manager,Imported with company creation\n"
        ),
        create_missing_companies=True,
    )

    assert result.imported_rows == 1
    assert result.error_rows == 0
    assert any(company["name"] == "Fresh Company" for company in session.companies.values())


@pytest.mark.asyncio
async def test_export_contacts_csv_respects_tenant_scope_and_filters() -> None:
    session = FakeCrmImportSession()
    session.contacts["contact-second"] = {
        "id": "contact-second",
        "tenant_id": "tenant-1",
        "first_name": "Alicia",
        "last_name": "Andersson",
        "email": "alicia@example.com",
        "phone": "+46700000000",
        "company_id": "company-1",
        "company": "Northwind",
        "job_title": "Buyer",
        "notes": "Campaign target",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    session.contacts["contact-other-tenant"] = {
        "id": "contact-other-tenant",
        "tenant_id": "tenant-2",
        "first_name": "Other",
        "last_name": "Tenant",
        "email": "other@example.com",
        "phone": None,
        "company_id": "company-2",
        "company": "Outside Tenant",
        "job_title": None,
        "notes": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    csv_text, row_count = await export_contacts_csv(
        session,
        tenant_id="tenant-1",
        q="alicia",
        company_id="company-1",
    )

    assert row_count == 1
    assert "Alicia,Andersson,alicia@example.com" in csv_text
    assert "other@example.com" not in csv_text
