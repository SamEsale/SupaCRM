import os
import psycopg

DSN = os.getenv("postgresql+psycopg://postgres:SupaCRM@localhost:5432/supacrm")
assert DSN, "Missing DATABASE_URL_SYNC"

SQL = """
SELECT
  t.id,
  t.name,
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
        for tid, name, rc, tuc in rows:
            print(f"{tid}  name={name!r}  roles={rc}  tenant_users={tuc}")
