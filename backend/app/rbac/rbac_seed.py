"""
Canonical RBAC seed definitions for SupaCRM.

This module defines the authoritative list of:
- default roles
- default permissions
- permission descriptions
- role-permission mappings

All tenant bootstrap operations must use this module.
"""

from typing import Final


# -----------------------------------------------------
# Permission Definitions
# -----------------------------------------------------

CRM_READ: Final[str] = "crm.read"
CRM_WRITE: Final[str] = "crm.write"
CRM_DELETE: Final[str] = "crm.delete"

SALES_READ: Final[str] = "sales.read"
SALES_WRITE: Final[str] = "sales.write"
SALES_DELETE: Final[str] = "sales.delete"

REPORTING_READ: Final[str] = "reporting.read"

SUPPORT_READ: Final[str] = "support.read"
SUPPORT_WRITE: Final[str] = "support.write"

BILLING_ACCESS: Final[str] = "billing.access"
TENANT_ADMIN: Final[str] = "tenant.admin"


DEFAULT_PERMISSIONS: Final[tuple[str, ...]] = (
    CRM_READ,
    CRM_WRITE,
    CRM_DELETE,
    SALES_READ,
    SALES_WRITE,
    SALES_DELETE,
    REPORTING_READ,
    SUPPORT_READ,
    SUPPORT_WRITE,
    BILLING_ACCESS,
    TENANT_ADMIN,
)


PERMISSION_DESCRIPTIONS: Final[dict[str, str]] = {
    CRM_READ: "Read CRM records",
    CRM_WRITE: "Create and update CRM records",
    CRM_DELETE: "Delete CRM records",
    SALES_READ: "Read sales data",
    SALES_WRITE: "Create and update sales data",
    SALES_DELETE: "Delete sales data",
    REPORTING_READ: "Read reports and dashboards",
    SUPPORT_READ: "Read support data",
    SUPPORT_WRITE: "Create and update support data",
    BILLING_ACCESS: "Access billing and subscription features",
    TENANT_ADMIN: "Manage tenant administration settings",
}


# -----------------------------------------------------
# Role Definitions
# -----------------------------------------------------

OWNER: Final[str] = "owner"
ADMIN: Final[str] = "admin"
MANAGER: Final[str] = "manager"
USER: Final[str] = "user"


DEFAULT_ROLES: Final[tuple[str, ...]] = (
    OWNER,
    ADMIN,
    MANAGER,
    USER,
)


# -----------------------------------------------------
# Role → Permission Mapping
# -----------------------------------------------------

DEFAULT_ROLE_PERMISSIONS: Final[dict[str, tuple[str, ...]]] = {
    OWNER: (
        CRM_READ,
        CRM_WRITE,
        CRM_DELETE,
        SALES_READ,
        SALES_WRITE,
        SALES_DELETE,
        REPORTING_READ,
        SUPPORT_READ,
        SUPPORT_WRITE,
        BILLING_ACCESS,
        TENANT_ADMIN,
    ),
    ADMIN: (
        CRM_READ,
        CRM_WRITE,
        CRM_DELETE,
        SALES_READ,
        SALES_WRITE,
        SALES_DELETE,
        REPORTING_READ,
        SUPPORT_READ,
        SUPPORT_WRITE,
        BILLING_ACCESS,
        TENANT_ADMIN,
    ),
    MANAGER: (
        CRM_READ,
        CRM_WRITE,
        SALES_READ,
        SALES_WRITE,
        REPORTING_READ,
        SUPPORT_READ,
        SUPPORT_WRITE,
    ),
    USER: (
        CRM_READ,
        SALES_READ,
        SUPPORT_READ,
    ),
}


def get_default_permission_rows() -> tuple[tuple[str, str], ...]:
    """
    Returns deterministic permission rows as:
        (permission_code, permission_description)
    """
    return tuple((code, PERMISSION_DESCRIPTIONS[code]) for code in DEFAULT_PERMISSIONS)