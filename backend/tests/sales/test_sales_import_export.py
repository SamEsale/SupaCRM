from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.sales.service import export_leads_csv, import_leads_from_csv


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
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        scalar: Any = None,
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self) -> _FakeMappings:
        return _FakeMappings(self._rows)

    def scalar_one(self) -> Any:
        return self._scalar

    def scalar_one_or_none(self) -> Any:
        return self._scalar


class FakeLeadImportSession:
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
            "contact-1": {
                "id": "contact-1",
                "tenant_id": "tenant-1",
                "first_name": "Alicia",
                "last_name": "Andersson",
                "email": "alicia@example.com",
                "phone": "+46700000000",
                "company_id": "company-1",
                "company": "Northwind",
                "job_title": None,
                "notes": None,
                "created_at": now,
                "updated_at": now,
            }
        }
        self.deals: dict[str, dict[str, Any]] = {
            "deal-export": {
                "id": "deal-export",
                "tenant_id": "tenant-1",
                "name": "Renewal Lead",
                "company_id": "company-1",
                "contact_id": "contact-1",
                "product_id": None,
                "amount": Decimal("1200.00"),
                "currency": "USD",
                "stage": "qualified lead",
                "status": "open",
                "expected_close_date": None,
                "notes": "Campaign ready",
                "next_follow_up_at": None,
                "follow_up_note": None,
                "closed_at": None,
                "created_at": now,
                "updated_at": now,
            },
            "deal-other-tenant": {
                "id": "deal-other-tenant",
                "tenant_id": "tenant-2",
                "name": "Outside lead",
                "company_id": "company-2",
                "contact_id": None,
                "product_id": None,
                "amount": Decimal("50.00"),
                "currency": "USD",
                "stage": "new lead",
                "status": "open",
                "expected_close_date": None,
                "notes": None,
                "next_follow_up_at": None,
                "follow_up_note": None,
                "closed_at": None,
                "created_at": now,
                "updated_at": now,
            },
        }

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql = " ".join(str(statement).split()).lower()
        payload = params or {}

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

        if "from public.contacts" in sql and "company_id = cast(:company_id as varchar)" in sql and "or (:email is not null" in sql:
            for contact in self.contacts.values():
                if contact["tenant_id"] != str(payload["tenant_id"]):
                    continue
                if contact["company_id"] != str(payload["company_id"]):
                    continue
                email_matches = payload.get("email") and contact["email"] and str(contact["email"]).lower() == str(payload["email"]).lower()
                phone_matches = payload.get("phone") and contact["phone"] == payload.get("phone")
                if email_matches or phone_matches:
                    return _FakeResult(rows=[dict(contact)])
            return _FakeResult(rows=[])

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

        if "select 1 from public.companies" in sql:
            company = self.companies.get(str(payload["company_id"]))
            if company and company["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select 1 from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if contact and contact["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(scalar=1)
            return _FakeResult(scalar=None)

        if "select company_id from public.contacts" in sql:
            contact = self.contacts.get(str(payload["contact_id"]))
            if contact and contact["tenant_id"] == str(payload["tenant_id"]):
                return _FakeResult(rows=[{"company_id": contact["company_id"]}])
            return _FakeResult(rows=[])

        if "insert into public.deals" in sql:
            row = {
                "id": str(payload["id"]),
                "tenant_id": str(payload["tenant_id"]),
                "name": str(payload["name"]),
                "company_id": str(payload["company_id"]),
                "contact_id": payload.get("contact_id"),
                "product_id": payload.get("product_id"),
                "amount": Decimal(str(payload["amount"])),
                "currency": str(payload["currency"]),
                "stage": str(payload["stage"]),
                "status": str(payload["status"]),
                "expected_close_date": payload.get("expected_close_date"),
                "notes": payload.get("notes"),
                "next_follow_up_at": payload.get("next_follow_up_at"),
                "follow_up_note": payload.get("follow_up_note"),
                "closed_at": payload.get("closed_at"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            self.deals[row["id"]] = row
            return _FakeResult(rows=[dict(row)])

        if "from public.deals d" in sql and "d.stage in ('new lead', 'qualified lead')" in sql:
            rows = [
                {
                    "name": deal["name"],
                    "company_name": self.companies[deal["company_id"]]["name"],
                    "first_name": self.contacts[deal["contact_id"]]["first_name"] if deal["contact_id"] else None,
                    "last_name": self.contacts[deal["contact_id"]]["last_name"] if deal["contact_id"] else None,
                    "email": self.contacts[deal["contact_id"]]["email"] if deal["contact_id"] else None,
                    "phone": self.contacts[deal["contact_id"]]["phone"] if deal["contact_id"] else None,
                    "amount": deal["amount"],
                    "currency": deal["currency"],
                    "stage": deal["stage"],
                    "status": deal["status"],
                    "notes": deal["notes"],
                }
                for deal in self.deals.values()
                if deal["tenant_id"] == str(payload["tenant_id"]) and deal["stage"] in {"new lead", "qualified lead"}
            ]
            search = str(payload.get("search", "")).replace("%", "").lower()
            if search:
                rows = [
                    row
                    for row in rows
                    if search in " ".join(
                        [
                            str(row["name"] or ""),
                            str(row["company_name"] or ""),
                            str(row["first_name"] or ""),
                            str(row["last_name"] or ""),
                            str(row["email"] or ""),
                            str(row["stage"] or ""),
                            str(row["status"] or ""),
                            str(row["notes"] or ""),
                        ]
                    ).lower()
                ]
            company_id = payload.get("company_id")
            if company_id:
                rows = [row for row in rows if any(
                    deal["company_id"] == str(company_id) and deal["name"] == row["name"]
                    for deal in self.deals.values()
                )]
            contact_id = payload.get("contact_id")
            if contact_id:
                rows = [row for row in rows if any(
                    deal["contact_id"] == str(contact_id) and deal["name"] == row["name"]
                    for deal in self.deals.values()
                )]
            rows.sort(key=lambda row: (str(row["name"]), str(row["email"] or "")))
            return _FakeResult(rows=rows)

        raise AssertionError(f"Unhandled SQL in FakeLeadImportSession: {sql}")


@pytest.mark.asyncio
async def test_import_leads_creates_real_deal_records_and_links_contacts() -> None:
    session = FakeLeadImportSession()

    result = await import_leads_from_csv(
        session,
        tenant_id="tenant-1",
        csv_text=(
            "name,company,first_name,last_name,email,phone,amount,currency,stage,status,source,notes\n"
            "Spring Outreach,Northwind,Alicia,Andersson,alicia@example.com,+46700000000,1500,usd,qualified lead,open,email,Ready for campaign\n"
        ),
        create_missing_companies=False,
    )

    assert result.imported_rows == 1
    assert result.error_rows == 0
    imported_deals = [deal for deal in session.deals.values() if deal["name"] == "Spring Outreach"]
    assert len(imported_deals) == 1
    assert imported_deals[0]["stage"] == "qualified lead"
    assert imported_deals[0]["status"] == "open"
    assert imported_deals[0]["contact_id"] == "contact-1"
    assert "Lead source: email" in str(imported_deals[0]["notes"])


@pytest.mark.asyncio
async def test_import_leads_rejects_invalid_stage_values() -> None:
    session = FakeLeadImportSession()

    result = await import_leads_from_csv(
        session,
        tenant_id="tenant-1",
        csv_text=(
            "name,company,first_name,last_name,email,phone,amount,currency,stage,status,notes\n"
            "Closed Revenue,Northwind,Alicia,Andersson,alicia@example.com,+46700000000,1500,USD,contract signed,won,Should fail\n"
        ),
    )

    assert result.imported_rows == 0
    assert result.error_rows == 1
    assert "Lead imports only support the stages" in result.rows[0].message


@pytest.mark.asyncio
async def test_export_leads_csv_respects_tenant_scope_and_search_filters() -> None:
    session = FakeLeadImportSession()

    csv_text, row_count = await export_leads_csv(
        session,
        tenant_id="tenant-1",
        q="renewal",
    )

    assert row_count == 1
    assert "Renewal Lead,Northwind,Alicia,Andersson,alicia@example.com" in csv_text
    assert "Outside lead" not in csv_text
