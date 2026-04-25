from __future__ import annotations

import os
import sys
from pathlib import Path
import uuid

# --- Make sure "backend/" is on sys.path so "import app" always works ---
BACKEND_DIR = Path(__file__).resolve().parents[1]   # ...\backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_supa
load_env_supa()

from sqlalchemy import create_engine, text

DSN = os.getenv("DATABASE_URL_SYNC")
assert DSN, "Missing DATABASE_URL_SYNC"

TENANT_ID = os.getenv("DEV_TENANT_ID")  # optional convenience
DEFAULT_TENANT = "110824ad-8a94-4fbb-9a3b-abb6d27831b9"
tenant_id = (TENANT_ID or DEFAULT_TENANT).strip()

PERM_CODE = "audit.write"
ROLE_NAME = "admin"

def gen_id() -> str:
    return str(uuid.uuid4())

engine = create_engine(DSN)

with engine.begin() as conn:
    # 1) Ensure permission exists
    perm_id = conn.execute(
        text("SELECT id FROM public.permissions WHERE code = :code"),
        {"code": PERM_CODE},
    ).scalar_one_or_none()

    if not perm_id:
        perm_id = gen_id()
        conn.execute(
            text("""
                INSERT INTO public.permissions (id, code, description)
                VALUES (:id, :code, :desc)
            """),
            {"id": perm_id, "code": PERM_CODE, "desc": "Write audit logs"},
        )
        print(f"Created permission {PERM_CODE} id={perm_id}")
    else:
        print(f"Permission {PERM_CODE} exists id={perm_id}")

    # 2) Find admin role for this tenant
    role_id = conn.execute(
        text("""
            SELECT id
            FROM public.roles
            WHERE tenant_id = :tenant_id
              AND name = :name
            LIMIT 1
        """),
        {"tenant_id": tenant_id, "name": ROLE_NAME},
    ).scalar_one_or_none()

    if not role_id:
        raise SystemExit(f"ERROR: No role named '{ROLE_NAME}' found for tenant {tenant_id}")

    print(f"Tenant admin role id={role_id}")

    # 3) Ensure role_permissions mapping exists
    exists = conn.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM public.role_permissions
                WHERE role_id = :role_id AND permission_id = :perm_id
            )
        """),
        {"role_id": role_id, "perm_id": perm_id},
    ).scalar_one()

    if exists:
        print("role_permissions already has audit.write for this role.")
    else:
        conn.execute(
            text("""
                INSERT INTO public.role_permissions (role_id, permission_id)
                VALUES (:role_id, :perm_id)
            """),
            {"role_id": role_id, "perm_id": perm_id},
        )
        print("Granted audit.write to tenant admin role via role_permissions.")

print("DONE.")
