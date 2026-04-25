from sqlalchemy import Boolean, Column, DateTime, JSON, Numeric, String, func
from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    # Use String(64) to align with tenant header usage and RLS GUC patterns.
    id = Column(String(64), primary_key=True)

    name = Column(String(255), nullable=False)

    # Legacy boolean retained for backward compatibility with current auth flow.
    is_active = Column(Boolean, nullable=False, server_default="true")

    # Explicit lifecycle status for Phase 2.5
    status = Column(String(32), nullable=False, server_default="active")
    status_reason = Column(String(255), nullable=True)
    legal_name = Column(String(255), nullable=True)
    address_line_1 = Column(String(255), nullable=True)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(120), nullable=True)
    state_region = Column(String(120), nullable=True)
    postal_code = Column(String(40), nullable=True)
    country = Column(String(120), nullable=True)
    vat_number = Column(String(64), nullable=True)
    default_currency = Column(String(3), nullable=False, server_default="USD")
    secondary_currency = Column(String(3), nullable=True)
    secondary_currency_rate = Column(Numeric(18, 6), nullable=True)
    secondary_currency_rate_source = Column(String(64), nullable=True)
    secondary_currency_rate_as_of = Column(DateTime(timezone=True), nullable=True)
    logo_file_key = Column(String(512), nullable=True)
    brand_primary_color = Column(String(7), nullable=True)
    brand_secondary_color = Column(String(7), nullable=True)
    sidebar_background_color = Column(String(7), nullable=True)
    sidebar_text_color = Column(String(7), nullable=True)
    whatsapp_settings = Column(JSON, nullable=False, server_default="{}")
    smtp_settings = Column(JSON, nullable=False, server_default="{}")
    payment_gateway_settings = Column(JSON, nullable=False, server_default="{}")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
