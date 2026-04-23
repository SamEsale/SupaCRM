from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.service import sync_payment_accounting_entries


ALLOWED_PAYMENT_METHODS: tuple[str, ...] = (
    "bank_transfer",
    "cash",
    "card_manual",
    "other",
)

ALLOWED_PAYMENT_STATUSES: tuple[str, ...] = (
    "pending",
    "completed",
    "failed",
    "cancelled",
)

PAYMENT_STATE_UNPAID = "unpaid"
PAYMENT_STATE_PARTIALLY_PAID = "partially paid"
PAYMENT_STATE_PAID = "paid"


@dataclass(slots=True)
class InvoicePaymentDetails:
    id: str
    tenant_id: str
    invoice_id: str
    amount: Decimal
    currency: str
    method: str
    status: str
    payment_date: datetime
    external_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class InvoicePaymentListResult:
    items: list[InvoicePaymentDetails]
    total: int


@dataclass(slots=True)
class InvoicePaymentSummary:
    invoice_id: str
    currency: str
    invoice_total_amount: Decimal
    completed_amount: Decimal
    pending_amount: Decimal
    outstanding_amount: Decimal
    payment_count: int
    completed_payment_count: int
    pending_payment_count: int
    payment_state: str


@dataclass(slots=True)
class InvoicePaymentInvoiceContext:
    id: str
    tenant_id: str
    number: str
    currency: str
    total_amount: Decimal
    status: str
    issue_date: datetime
    notes: str | None


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a valid ISO 4217 uppercase 3-letter code")
    return normalized


def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
    if isinstance(value, Decimal):
        normalized = value
    else:
        try:
            normalized = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Payment amounts must be valid decimal values") from exc

    if normalized <= 0:
        raise ValueError("Payment amount must be greater than zero")

    return normalized.quantize(Decimal("0.01"))


def _normalize_method(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_PAYMENT_METHODS:
        raise ValueError(
            "Invalid payment method. Allowed values: " + ", ".join(ALLOWED_PAYMENT_METHODS)
        )
    return normalized


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_PAYMENT_STATUSES:
        raise ValueError(
            "Invalid payment status. Allowed values: " + ", ".join(ALLOWED_PAYMENT_STATUSES)
        )
    return normalized


def _payment_from_row(row: dict[str, object]) -> InvoicePaymentDetails:
    return InvoicePaymentDetails(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        invoice_id=str(row["invoice_id"]),
        amount=Decimal(str(row["amount"])),
        currency=str(row["currency"]),
        method=str(row["method"]),
        status=str(row["status"]),
        payment_date=row["payment_date"],
        external_reference=row["external_reference"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def _get_invoice_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> InvoicePaymentInvoiceContext | None:
    result = await session.execute(
        text(
            """
            select
                id,
                tenant_id,
                number,
                currency,
                total_amount,
                status,
                issue_date,
                notes
            from public.invoices
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:invoice_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    row = result.mappings().first()
    if not row:
        return None

    issue_date = row["issue_date"]
    issue_datetime = datetime.combine(issue_date, datetime.min.time(), tzinfo=UTC)
    return InvoicePaymentInvoiceContext(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        number=str(row["number"]),
        currency=str(row["currency"]),
        total_amount=Decimal(str(row["total_amount"])),
        status=str(row["status"]),
        issue_date=issue_datetime,
        notes=row["notes"],
    )


async def _set_invoice_status(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
    status: str,
) -> None:
    await session.execute(
        text(
            """
            update public.invoices
            set status = cast(:status as varchar),
                updated_at = now()
            where tenant_id = cast(:tenant_id as varchar)
              and id = cast(:invoice_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "status": status,
        },
    )


async def get_invoice_completed_payment_total(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> Decimal:
    result = await session.execute(
        text(
            """
            select coalesce(sum(amount), 0)
            from public.invoice_payments
            where tenant_id = cast(:tenant_id as varchar)
              and invoice_id = cast(:invoice_id as varchar)
              and status = 'completed'
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    return Decimal(str(result.scalar_one() or "0"))


async def has_invoice_payments(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> bool:
    result = await session.execute(
        text(
            """
            select 1
            from public.invoice_payments
            where tenant_id = cast(:tenant_id as varchar)
              and invoice_id = cast(:invoice_id as varchar)
            limit 1
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    return result.scalar_one_or_none() == 1


async def get_invoice_payment_summary(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> InvoicePaymentSummary:
    invoice = await _get_invoice_for_tenant(session, tenant_id=tenant_id, invoice_id=invoice_id)
    if invoice is None:
        raise ValueError(f"Invoice does not exist: {invoice_id}")

    result = await session.execute(
        text(
            """
            select
                count(*) as payment_count,
                coalesce(sum(case when status = 'completed' then amount else 0 end), 0) as completed_amount,
                coalesce(sum(case when status = 'pending' then amount else 0 end), 0) as pending_amount,
                count(*) filter (where status = 'completed') as completed_payment_count,
                count(*) filter (where status = 'pending') as pending_payment_count
            from public.invoice_payments
            where tenant_id = cast(:tenant_id as varchar)
              and invoice_id = cast(:invoice_id as varchar)
            """
        ),
        {"tenant_id": tenant_id, "invoice_id": invoice_id},
    )
    row = result.mappings().first() or {
        "payment_count": 0,
        "completed_amount": Decimal("0.00"),
        "pending_amount": Decimal("0.00"),
        "completed_payment_count": 0,
        "pending_payment_count": 0,
    }

    completed_amount = Decimal(str(row["completed_amount"] or "0"))
    pending_amount = Decimal(str(row["pending_amount"] or "0"))
    outstanding_amount = max(invoice.total_amount - completed_amount, Decimal("0.00"))

    if completed_amount == Decimal("0.00"):
        payment_state = PAYMENT_STATE_UNPAID
    elif outstanding_amount == Decimal("0.00"):
        payment_state = PAYMENT_STATE_PAID
    else:
        payment_state = PAYMENT_STATE_PARTIALLY_PAID

    return InvoicePaymentSummary(
        invoice_id=invoice.id,
        currency=invoice.currency,
        invoice_total_amount=invoice.total_amount,
        completed_amount=completed_amount,
        pending_amount=pending_amount,
        outstanding_amount=outstanding_amount,
        payment_count=int(row["payment_count"] or 0),
        completed_payment_count=int(row["completed_payment_count"] or 0),
        pending_payment_count=int(row["pending_payment_count"] or 0),
        payment_state=payment_state,
    )


async def create_invoice_payment(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
    amount: Decimal,
    currency: str,
    method: str,
    status: str,
    payment_date: datetime,
    external_reference: str | None = None,
    notes: str | None = None,
) -> InvoicePaymentDetails:
    invoice = await _get_invoice_for_tenant(session, tenant_id=tenant_id, invoice_id=invoice_id)
    if invoice is None:
        raise ValueError(f"Invoice does not exist: {invoice_id}")

    normalized_amount = _normalize_amount(amount)
    normalized_currency = _normalize_currency(currency)
    normalized_method = _normalize_method(method)
    normalized_status = _normalize_status(status)
    normalized_reference = _clean_optional(external_reference)
    normalized_notes = _clean_optional(notes)

    if invoice.status == "draft":
        raise ValueError("Payments can only be recorded after an invoice has been issued")
    if invoice.status == "cancelled":
        raise ValueError("Cancelled invoices cannot accept payments")

    if normalized_currency != invoice.currency:
        raise ValueError(
            f"Payment currency must match the invoice currency: {normalized_currency} != {invoice.currency}"
        )

    summary = await get_invoice_payment_summary(session, tenant_id=tenant_id, invoice_id=invoice_id)

    if summary.outstanding_amount == Decimal("0.00"):
        raise ValueError("This invoice has already been fully paid")

    if normalized_status == "completed" and normalized_amount > summary.outstanding_amount:
        raise ValueError(
            f"Payment amount exceeds the outstanding invoice balance: {normalized_amount} > {summary.outstanding_amount}"
        )

    payment_id = str(uuid.uuid4())
    result = await session.execute(
        text(
            """
            insert into public.invoice_payments (
                id,
                tenant_id,
                invoice_id,
                amount,
                currency,
                method,
                status,
                payment_date,
                external_reference,
                notes
            )
            values (
                cast(:id as varchar),
                cast(:tenant_id as varchar),
                cast(:invoice_id as varchar),
                :amount,
                cast(:currency as varchar),
                cast(:method as varchar),
                cast(:status as varchar),
                :payment_date,
                :external_reference,
                :notes
            )
            returning
                id,
                tenant_id,
                invoice_id,
                amount,
                currency,
                method,
                status,
                payment_date,
                external_reference,
                notes,
                created_at,
                updated_at
            """
        ),
        {
            "id": payment_id,
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
            "amount": normalized_amount,
            "currency": normalized_currency,
            "method": normalized_method,
            "status": normalized_status,
            "payment_date": payment_date,
            "external_reference": normalized_reference,
            "notes": normalized_notes,
        },
    )
    row = result.mappings().first()
    if not row:
        raise ValueError("Failed to record payment")

    payment = _payment_from_row(row)

    if payment.status == "completed":
        await sync_payment_accounting_entries(
            session,
            tenant_id=tenant_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            invoice_number=invoice.number,
            payment_date=payment.payment_date,
            currency=payment.currency,
            amount=payment.amount,
            memo=payment.notes,
        )

        next_summary = await get_invoice_payment_summary(session, tenant_id=tenant_id, invoice_id=invoice_id)
        if next_summary.outstanding_amount == Decimal("0.00") and invoice.status != "paid":
            await _set_invoice_status(
                session,
                tenant_id=tenant_id,
                invoice_id=invoice_id,
                status="paid",
            )

    return payment


async def list_invoice_payments(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str | None = None,
    status: str | None = None,
    method: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> InvoicePaymentListResult:
    normalized_invoice_id = _clean_optional(invoice_id)
    normalized_status = _normalize_status(status) if status else None
    normalized_method = _normalize_method(method) if method else None

    count_sql = """
        select count(*)
        from public.invoice_payments
        where tenant_id = cast(:tenant_id as varchar)
    """
    list_sql = """
        select
            id,
            tenant_id,
            invoice_id,
            amount,
            currency,
            method,
            status,
            payment_date,
            external_reference,
            notes,
            created_at,
            updated_at
        from public.invoice_payments
        where tenant_id = cast(:tenant_id as varchar)
    """
    params: dict[str, object] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
    }

    if normalized_invoice_id:
        count_sql += " and invoice_id = cast(:invoice_id as varchar) "
        list_sql += " and invoice_id = cast(:invoice_id as varchar) "
        params["invoice_id"] = normalized_invoice_id

    if normalized_status:
        count_sql += " and status = cast(:status as varchar) "
        list_sql += " and status = cast(:status as varchar) "
        params["status"] = normalized_status

    if normalized_method:
        count_sql += " and method = cast(:method as varchar) "
        list_sql += " and method = cast(:method as varchar) "
        params["method"] = normalized_method

    list_sql += """
        order by payment_date desc, created_at desc, id desc
        limit :limit
        offset :offset
    """

    total = int((await session.execute(text(count_sql), params)).scalar_one())
    rows = list((await session.execute(text(list_sql), params)).mappings())

    return InvoicePaymentListResult(
        items=[_payment_from_row(row) for row in rows],
        total=total,
    )
