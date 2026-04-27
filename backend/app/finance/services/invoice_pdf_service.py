from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class InvoicePdfLineItem:
    name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


@dataclass(slots=True)
class InvoicePdfContext:
    tenant_name: str
    brand_primary_color: str | None
    brand_secondary_color: str | None
    invoice_id: str
    invoice_number: str
    issue_date: date
    due_date: date
    currency: str
    status: str
    customer_name: str
    customer_email: str | None
    customer_phone: str | None
    customer_address: str | None
    customer_vat_number: str | None
    line_items: list[InvoicePdfLineItem]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    notes: str | None


def _format_money(amount: Decimal, currency: str) -> str:
    return f"{currency} {amount.quantize(Decimal('0.01')):,.2f}"


def _normalize_hex_color(value: str | None, fallback: colors.Color) -> colors.Color:
    if not value:
        return fallback
    try:
        return colors.HexColor(value)
    except Exception:
        return fallback


def _build_line_items(row: dict[str, object]) -> list[InvoicePdfLineItem]:
    total = Decimal(str(row["total_amount"]))
    product_name = str(row["product_name"] or "Invoice item")
    product_unit_price_raw = row.get("product_unit_price")

    if product_unit_price_raw is None:
        return [
            InvoicePdfLineItem(
                name=product_name,
                quantity=Decimal("1.00"),
                unit_price=total,
                line_total=total,
            )
        ]

    unit_price = Decimal(str(product_unit_price_raw))
    if unit_price <= 0:
        unit_price = total

    if unit_price == total:
        quantity = Decimal("1.00")
    else:
        quantity = Decimal("1.00")
        unit_price = total

    return [
        InvoicePdfLineItem(
            name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            line_total=total,
        )
    ]


async def get_invoice_pdf_context(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> InvoicePdfContext | None:
    result = await session.execute(
        text(
            """
            select
                i.id as invoice_id,
                i.number as invoice_number,
                i.issue_date,
                i.due_date,
                i.currency,
                i.status,
                i.total_amount,
                i.notes,
                t.name as tenant_name,
                t.brand_primary_color,
                t.brand_secondary_color,
                c.name as company_name,
                c.email as company_email,
                c.phone as company_phone,
                c.address as company_address,
                c.vat_number as company_vat_number,
                ct.first_name as contact_first_name,
                ct.last_name as contact_last_name,
                ct.email as contact_email,
                ct.phone as contact_phone,
                p.name as product_name,
                p.unit_price as product_unit_price
            from public.invoices i
            join public.tenants t
              on t.id = i.tenant_id
            join public.companies c
              on c.id = i.company_id
             and c.tenant_id = i.tenant_id
            left join public.contacts ct
              on ct.id = i.contact_id
             and ct.tenant_id = i.tenant_id
            left join public.products p
              on p.id = i.product_id
             and p.tenant_id = i.tenant_id
            where i.tenant_id = cast(:tenant_id as varchar)
              and i.id = cast(:invoice_id as varchar)
            """
        ),
        {
            "tenant_id": tenant_id,
            "invoice_id": invoice_id,
        },
    )
    row = result.mappings().first()
    if not row:
        return None

    contact_parts = [
        str(row["contact_first_name"]).strip() if row["contact_first_name"] else "",
        str(row["contact_last_name"]).strip() if row["contact_last_name"] else "",
    ]
    contact_name = " ".join(part for part in contact_parts if part).strip()
    customer_name = contact_name or str(row["company_name"])
    customer_email = row["contact_email"] or row["company_email"]
    customer_phone = row["contact_phone"] or row["company_phone"]

    subtotal = Decimal(str(row["total_amount"]))
    tax = Decimal("0.00")
    line_items = _build_line_items(row)

    return InvoicePdfContext(
        tenant_name=str(row["tenant_name"]),
        brand_primary_color=row["brand_primary_color"],
        brand_secondary_color=row["brand_secondary_color"],
        invoice_id=str(row["invoice_id"]),
        invoice_number=str(row["invoice_number"]),
        issue_date=row["issue_date"],
        due_date=row["due_date"],
        currency=str(row["currency"]),
        status=str(row["status"]),
        customer_name=customer_name,
        customer_email=str(customer_email) if customer_email else None,
        customer_phone=str(customer_phone) if customer_phone else None,
        customer_address=str(row["company_address"]) if row["company_address"] else None,
        customer_vat_number=str(row["company_vat_number"]) if row["company_vat_number"] else None,
        line_items=line_items,
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        notes=str(row["notes"]) if row["notes"] else None,
    )


async def build_invoice_pdf(
    session: AsyncSession,
    *,
    tenant_id: str,
    invoice_id: str,
) -> bytes | None:
    context = await get_invoice_pdf_context(
        session,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
    )
    if context is None:
        return None

    primary_color = _normalize_hex_color(context.brand_primary_color, colors.HexColor("#2563EB"))
    secondary_color = _normalize_hex_color(context.brand_secondary_color, colors.HexColor("#E2E8F0"))

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Invoice {context.invoice_number}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        textColor=primary_color,
        spaceAfter=6,
    )
    small_label_style = ParagraphStyle(
        "SmallLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=colors.HexColor("#475569"),
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "InvoiceBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
    )
    right_body_style = ParagraphStyle(
        "InvoiceBodyRight",
        parent=body_style,
        alignment=TA_RIGHT,
    )

    story: list[object] = [
        Paragraph(context.tenant_name, title_style),
        Paragraph("Invoice", styles["Heading2"]),
        Spacer(1, 6),
    ]

    header_table = Table(
        [
            [
                [
                    Paragraph("<b>Bill to</b>", small_label_style),
                    Paragraph(context.customer_name, body_style),
                    Paragraph(context.customer_email or "", body_style),
                    Paragraph(context.customer_phone or "", body_style),
                    Paragraph(context.customer_address or "", body_style),
                    Paragraph(
                        f"VAT / Tax ID: {context.customer_vat_number}" if context.customer_vat_number else "",
                        body_style,
                    ),
                ],
                [
                    Paragraph("<b>Invoice number</b>", small_label_style),
                    Paragraph(context.invoice_number, right_body_style),
                    Paragraph("<b>Issue date</b>", small_label_style),
                    Paragraph(context.issue_date.isoformat(), right_body_style),
                    Paragraph("<b>Due date</b>", small_label_style),
                    Paragraph(context.due_date.isoformat(), right_body_style),
                    Paragraph("<b>Status</b>", small_label_style),
                    Paragraph(context.status.title(), right_body_style),
                ],
            ]
        ],
        colWidths=[100 * mm, 70 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.75, secondary_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, secondary_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.extend([header_table, Spacer(1, 12)])

    line_item_rows = [["Item", "Qty", "Unit price", "Line total"]]
    for item in context.line_items:
        line_item_rows.append(
            [
                item.name,
                f"{item.quantity.normalize()}",
                _format_money(item.unit_price, context.currency),
                _format_money(item.line_total, context.currency),
            ]
        )

    line_items_table = Table(
        line_item_rows,
        colWidths=[90 * mm, 20 * mm, 35 * mm, 35 * mm],
        repeatRows=1,
    )
    line_items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), primary_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([line_items_table, Spacer(1, 12)])

    totals_table = Table(
        [
            ["Subtotal", _format_money(context.subtotal, context.currency)],
            ["Tax", _format_money(context.tax, context.currency)],
            ["Total", _format_money(context.total, context.currency)],
        ],
        colWidths=[40 * mm, 40 * mm],
        hAlign="RIGHT",
    )
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, primary_color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([totals_table, Spacer(1, 12)])

    if context.notes:
        story.extend(
            [
                Paragraph("<b>Notes</b>", small_label_style),
                Paragraph(context.notes, body_style),
            ]
        )

    document.build(story)
    return buffer.getvalue()
