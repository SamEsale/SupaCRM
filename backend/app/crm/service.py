from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import uuid

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class ContactDetails:
    id: str
    tenant_id: str
    first_name: str
    last_name: str | None
    email: str | None
    phone: str | None
    company_id: str | None
    company: str | None
    job_title: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ContactListResult:
    items: list[ContactDetails]
    total: int


@dataclass(slots=True)
class CompanyDetails:
    id: str
    tenant_id: str
    name: str
    website: str | None
    email: str | None
    phone: str | None
    industry: str | None
    address: str | None
    vat_number: str | None
    registration_number: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class CompanyListResult:
    items: list[CompanyDetails]
    total: int


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


async def _get_company_name_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str | None,
) -> str | None:
    if company_id is None:
        return None

    result = await session.execute(
        text(
            """
            select name
            from public.companies
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:company_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "company_id": company_id,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Company does not exist")
    return str(row["name"])


async def create_contact(
    session: AsyncSession,
    *,
    tenant_id: str,
    first_name: str,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    company_id: str | None = None,
    company: str | None = None,
    job_title: str | None = None,
    notes: str | None = None,
) -> ContactDetails:
    contact_id = str(uuid.uuid4())
    effective_company_id = _clean_optional(company_id)
    effective_company = _clean_optional(company)

    if effective_company_id is not None:
        effective_company = await _get_company_name_by_id(
            session,
            tenant_id=tenant_id,
            company_id=effective_company_id,
        )

    try:
        result = await session.execute(
            text(
                """
                insert into public.contacts (
                    id,
                    tenant_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    company_id,
                    company,
                    job_title,
                    notes
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:first_name as varchar),
                    cast(:last_name as varchar),
                    cast(:email as varchar),
                    cast(:phone as varchar),
                    cast(:company_id as varchar),
                    cast(:company as varchar),
                    cast(:job_title as varchar),
                    :notes
                )
                returning
                    id,
                    tenant_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    company_id,
                    company,
                    job_title,
                    notes,
                    created_at,
                    updated_at
                """
            ),
            {
                "id": contact_id,
                "tenant_id": tenant_id,
                "first_name": first_name.strip(),
                "last_name": _clean_optional(last_name),
                "email": _normalize_email(email),
                "phone": _clean_optional(phone),
                "company_id": effective_company_id,
                "company": effective_company,
                "job_title": _clean_optional(job_title),
                "notes": _clean_optional(notes),
            },
        )
    except IntegrityError as exc:
        if "uq_contacts_tenant_email" in str(exc.orig):
            raise ValueError("A contact with that email already exists for this tenant") from exc
        raise

    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create contact")

    return ContactDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        first_name=str(row["first_name"]),
        last_name=row["last_name"],
        email=row["email"],
        phone=row["phone"],
        company_id=row["company_id"],
        company=row["company"],
        job_title=row["job_title"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_contact_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    contact_id: str,
) -> ContactDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                first_name,
                last_name,
                email,
                phone,
                company_id,
                company,
                job_title,
                notes,
                created_at,
                updated_at
            from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:contact_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "contact_id": contact_id},
    )
    row = result.mappings().first()
    if not row:
        return None

    return ContactDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        first_name=str(row["first_name"]),
        last_name=row["last_name"],
        email=row["email"],
        phone=row["phone"],
        company_id=row["company_id"],
        company=row["company"],
        job_title=row["job_title"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_contacts(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ContactListResult:
    search = _clean_optional(q)

    count_sql = """
        select count(*)
        from public.contacts
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            first_name,
            last_name,
            email,
            phone,
            company_id,
            company,
            job_title,
            notes,
            created_at,
            updated_at
        from public.contacts
        where tenant_id = cast(:tenant_id as varchar)
    """

    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
    }

    if search:
        search_clause = """
          and (
                lower(first_name) like :search
             or lower(coalesce(last_name, '')) like :search
             or lower(coalesce(email, '')) like :search
             or lower(coalesce(company, '')) like :search
          )
        """
        count_sql += search_clause
        list_sql += search_clause
        params["search"] = f"%{search.lower()}%"

    list_sql += """
        order by created_at desc, id desc
        limit :limit
        offset :offset
    """

    count_result = await session.execute(text(count_sql), params)
    total = int(count_result.scalar_one())

    rows_result = await session.execute(text(list_sql), params)

    items: list[ContactDetails] = []
    for row in rows_result.mappings():
        items.append(
            ContactDetails(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                first_name=str(row["first_name"]),
                last_name=row["last_name"],
                email=row["email"],
                phone=row["phone"],
                company_id=row["company_id"],
                company=row["company"],
                job_title=row["job_title"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return ContactListResult(items=items, total=total)


async def update_contact(
    session: AsyncSession,
    *,
    tenant_id: str,
    contact_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    company_id: str | None = None,
    company: str | None = None,
    job_title: str | None = None,
    notes: str | None = None,
) -> ContactDetails:
    existing = await get_contact_by_id(session, tenant_id=tenant_id, contact_id=contact_id)
    if existing is None:
        raise ValueError(f"Contact does not exist: {contact_id}")

    effective_first_name = first_name.strip() if first_name is not None else existing.first_name
    effective_last_name = _clean_optional(last_name) if last_name is not None else existing.last_name
    effective_email = _normalize_email(email) if email is not None else existing.email
    effective_phone = _clean_optional(phone) if phone is not None else existing.phone

    if company_id is not None:
        effective_company_id = _clean_optional(company_id)
    else:
        effective_company_id = existing.company_id

    if company_id is not None:
        if effective_company_id is None:
            effective_company = None
        else:
            effective_company = await _get_company_name_by_id(
                session,
                tenant_id=tenant_id,
                company_id=effective_company_id,
            )
    elif company is not None:
        effective_company = _clean_optional(company)
    else:
        effective_company = existing.company

    effective_job_title = _clean_optional(job_title) if job_title is not None else existing.job_title
    effective_notes = _clean_optional(notes) if notes is not None else existing.notes

    try:
        result = await session.execute(
            text(
                """
                update public.contacts
                set first_name = cast(:first_name as varchar),
                    last_name = cast(:last_name as varchar),
                    email = cast(:email as varchar),
                    phone = cast(:phone as varchar),
                    company_id = cast(:company_id as varchar),
                    company = cast(:company as varchar),
                    job_title = cast(:job_title as varchar),
                    notes = :notes,
                    updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and id = cast(:contact_id as varchar)
                returning
                    id,
                    tenant_id,
                    first_name,
                    last_name,
                    email,
                    phone,
                    company_id,
                    company,
                    job_title,
                    notes,
                    created_at,
                    updated_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "contact_id": contact_id,
                "first_name": effective_first_name,
                "last_name": effective_last_name,
                "email": effective_email,
                "phone": effective_phone,
                "company_id": effective_company_id,
                "company": effective_company,
                "job_title": effective_job_title,
                "notes": effective_notes,
            },
        )
    except IntegrityError as exc:
        if "uq_contacts_tenant_email" in str(exc.orig):
            raise ValueError("A contact with that email already exists for this tenant") from exc
        raise

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Contact does not exist: {contact_id}")

    return ContactDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        first_name=str(row["first_name"]),
        last_name=row["last_name"],
        email=row["email"],
        phone=row["phone"],
        company_id=row["company_id"],
        company=row["company"],
        job_title=row["job_title"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_company(
    session: AsyncSession,
    *,
    tenant_id: str,
    name: str,
    website: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    industry: str | None = None,
    address: str | None = None,
    vat_number: str | None = None,
    registration_number: str | None = None,
    notes: str | None = None,
) -> CompanyDetails:
    company_id = str(uuid.uuid4())

    try:
        result = await session.execute(
            text(
                """
                insert into public.companies (
                    id,
                    tenant_id,
                    name,
                    website,
                    email,
                    phone,
                    industry,
                    address,
                    vat_number,
                    registration_number,
                    notes
                )
                values (
                    cast(:id as varchar),
                    cast(:tenant_id as varchar),
                    cast(:name as varchar),
                    cast(:website as varchar),
                    cast(:email as varchar),
                    cast(:phone as varchar),
                    cast(:industry as varchar),
                    :address,
                    cast(:vat_number as varchar),
                    cast(:registration_number as varchar),
                    :notes
                )
                returning
                    id,
                    tenant_id,
                    name,
                    website,
                    email,
                    phone,
                    industry,
                    address,
                    vat_number,
                    registration_number,
                    notes,
                    created_at,
                    updated_at
                """
            ),
            {
                "id": company_id,
                "tenant_id": tenant_id,
                "name": name.strip(),
                "website": _clean_optional(website),
                "email": _normalize_email(email),
                "phone": _clean_optional(phone),
                "industry": _clean_optional(industry),
                "address": _clean_optional(address),
                "vat_number": _clean_optional(vat_number),
                "registration_number": _clean_optional(registration_number),
                "notes": _clean_optional(notes),
            },
        )
    except IntegrityError as exc:
        if "uq_companies_tenant_name" in str(exc.orig):
            raise ValueError("A company with that name already exists for this tenant") from exc
        raise

    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to create company")

    return CompanyDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        website=row["website"],
        email=row["email"],
        phone=row["phone"],
        industry=row["industry"],
        address=row["address"],
        vat_number=row["vat_number"],
        registration_number=row["registration_number"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def get_company_by_id(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> CompanyDetails | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                name,
                website,
                email,
                phone,
                industry,
                address,
                vat_number,
                registration_number,
                notes,
                created_at,
                updated_at
            from public.companies
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:company_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "company_id": company_id},
    )
    row = result.mappings().first()
    if not row:
        return None

    return CompanyDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        website=row["website"],
        email=row["email"],
        phone=row["phone"],
        industry=row["industry"],
        address=row["address"],
        vat_number=row["vat_number"],
        registration_number=row["registration_number"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def list_companies(
    session: AsyncSession,
    *,
    tenant_id: str,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> CompanyListResult:
    search = _clean_optional(q)

    count_sql = """
        select count(*)
        from public.companies
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            name,
            website,
            email,
            phone,
            industry,
            address,
            vat_number,
            registration_number,
            notes,
            created_at,
            updated_at
        from public.companies
        where tenant_id = cast(:tenant_id as varchar)
    """

    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
    }

    if search:
        search_clause = """
          and (
                lower(name) like :search
             or lower(coalesce(email, '')) like :search
             or lower(coalesce(website, '')) like :search
             or lower(coalesce(industry, '')) like :search
             or lower(coalesce(address, '')) like :search
             or lower(coalesce(vat_number, '')) like :search
             or lower(coalesce(registration_number, '')) like :search
          )
        """
        count_sql += search_clause
        list_sql += search_clause
        params["search"] = f"%{search.lower()}%"

    list_sql += """
        order by created_at desc, id desc
        limit :limit
        offset :offset
    """

    count_result = await session.execute(text(count_sql), params)
    total = int(count_result.scalar_one())

    rows_result = await session.execute(text(list_sql), params)

    items: list[CompanyDetails] = []
    for row in rows_result.mappings():
        items.append(
            CompanyDetails(
                id=str(row["id"]),
                tenant_id=str(row["tenant_id"]),
                name=str(row["name"]),
                website=row["website"],
                email=row["email"],
                phone=row["phone"],
                industry=row["industry"],
                address=row["address"],
                vat_number=row["vat_number"],
                registration_number=row["registration_number"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    return CompanyListResult(items=items, total=total)


async def update_company(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    name: str | None = None,
    website: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    industry: str | None = None,
    address: str | None = None,
    vat_number: str | None = None,
    registration_number: str | None = None,
    notes: str | None = None,
) -> CompanyDetails:
    existing = await get_company_by_id(session, tenant_id=tenant_id, company_id=company_id)
    if existing is None:
        raise ValueError(f"Company does not exist: {company_id}")

    effective_name = name.strip() if name is not None else existing.name
    effective_website = _clean_optional(website) if website is not None else existing.website
    effective_email = _normalize_email(email) if email is not None else existing.email
    effective_phone = _clean_optional(phone) if phone is not None else existing.phone
    effective_industry = _clean_optional(industry) if industry is not None else existing.industry
    effective_address = _clean_optional(address) if address is not None else existing.address
    effective_vat_number = _clean_optional(vat_number) if vat_number is not None else existing.vat_number
    effective_registration_number = (
        _clean_optional(registration_number)
        if registration_number is not None
        else existing.registration_number
    )
    effective_notes = _clean_optional(notes) if notes is not None else existing.notes

    try:
        result = await session.execute(
            text(
                """
                update public.companies
                set name = cast(:name as varchar),
                    website = cast(:website as varchar),
                    email = cast(:email as varchar),
                    phone = cast(:phone as varchar),
                    industry = cast(:industry as varchar),
                    address = :address,
                    vat_number = cast(:vat_number as varchar),
                    registration_number = cast(:registration_number as varchar),
                    notes = :notes,
                    updated_at = now()
                where tenant_id = cast(:tenant_id as varchar)
                  and id = cast(:company_id as varchar)
                returning
                    id,
                    tenant_id,
                    name,
                    website,
                    email,
                    phone,
                    industry,
                    address,
                    vat_number,
                    registration_number,
                    notes,
                    created_at,
                    updated_at
                """
            ),
            {
                "tenant_id": tenant_id,
                "company_id": company_id,
                "name": effective_name,
                "website": effective_website,
                "email": effective_email,
                "phone": effective_phone,
                "industry": effective_industry,
                "address": effective_address,
                "vat_number": effective_vat_number,
                "registration_number": effective_registration_number,
                "notes": effective_notes,
            },
        )
    except IntegrityError as exc:
        if "uq_companies_tenant_name" in str(exc.orig):
            raise ValueError("A company with that name already exists for this tenant") from exc
        raise

    row = result.mappings().first()
    if not row:
        raise ValueError(f"Company does not exist: {company_id}")

    return CompanyDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        website=row["website"],
        email=row["email"],
        phone=row["phone"],
        industry=row["industry"],
        address=row["address"],
        vat_number=row["vat_number"],
        registration_number=row["registration_number"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def delete_contact(
    session: AsyncSession,
    *,
    tenant_id: str,
    contact_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            delete from public.contacts
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:contact_id as varchar)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "contact_id": contact_id,
        },
    )
    row = result.first()
    return row is not None


async def delete_company(
    session: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            delete from public.companies
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:company_id as varchar)
            returning id
            """
        ),
        {
            "tenant_id": tenant_id,
            "company_id": company_id,
        },
    )
    row = result.first()
    return row is not None
