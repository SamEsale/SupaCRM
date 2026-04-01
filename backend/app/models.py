"""
Central model registry.

Purpose:
- A single import point that loads ALL SQLAlchemy ORM models so that:
  - Base.metadata is fully populated
  - Alembic autogenerate sees all tables consistently
  - Tests and scripts can import one module to register everything

Usage:
    import app.models  # noqa: F401
"""

# Important: Import model modules (not symbols) so side-effect registration runs.

# Audit
import app.audit.models  # noqa: F401

# Tenants (core + membership)
import app.tenants.models  # noqa: F401
import app.tenants.membership_models  # noqa: F401

# Auth / RBAC
import app.auth.models  # noqa: F401
import app.rbac.models  # noqa: F401

# CRM
import app.crm.models  # noqa: F401

# Sales / Finance
import app.sales.models  # noqa: F401
import app.invoicing.models  # noqa: F401
import app.quotes.models  # noqa: F401
