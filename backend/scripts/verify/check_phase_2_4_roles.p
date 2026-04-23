import psycopg

dsn = "postgresql://postgres:SupaCRM@localhost:5432/supacrm"

sql = """
select
  tu.tenant_id,
  u.email,
  tu.is_owner,
  array_agg(r.name order by r.name) as roles
from tenant_users tu
join users u on u.id = tu.user_id
left join tenant_user_roles tur
  on tur.tenant_id = tu.tenant_id
 and tur.user_id = tu.user_id
left join roles r
  on r.id = tur.role_id
 and r.tenant_id = tu.tenant_id
where tu.tenant_id = 'tenant-demo'
group by tu.tenant_id, u.email, tu.is_owner
order by u.email;
"""

with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            print(row)