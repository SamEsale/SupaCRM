import os

import psycopg

DSN = os.getenv("DATABASE_URL_SYNC")
assert DSN, "Missing DATABASE_URL_SYNC"

DSN = DSN.replace("postgresql+psycopg://", "postgresql://")

SQL = """
SELECT
  t.id,
  t.name,
  t.status,
  t.is_active,
  (SELECT count(*) FROM public.roles r WHERE r.tenant_id = t.id) AS roles_count,
  (SELECT count(*) FROM public.tenant_users tu WHERE tu.tenant_id = t.id) AS tenant_users_count
FROM public.tenants t
ORDER BY t.created_at DESC NULLS LAST, t.id
LIMIT 20;
"""

with psycopg.connect(DSN) as conn:
    with conn.cursor() as cur:
        cur.execute(SQL)
        rows = cur.fetchall()
        if not rows:
            print("No tenants found.")
        for tid, name, status_value, is_active, rc, tuc in rows:
            print(
                f"{tid}  name={name!r}  status={status_value!r}  "
                f"is_active={is_active}  roles={rc}  tenant_users={tuc}"
            )