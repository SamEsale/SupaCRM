import psycopg

dsn = "postgresql://postgres:SupaCRM@localhost:5432/supacrm"

queries = {
    "tenants": """
        SELECT id, name, is_active
        FROM tenants
        ORDER BY id;
    """,
    "users": """
        SELECT id, email, full_name, is_active, is_superuser
        FROM users
        ORDER BY email;
    """,
    "tenant_users": """
        SELECT tenant_id, user_id, is_owner, is_active
        FROM tenant_users
        ORDER BY tenant_id, user_id;
    """,
    "roles": """
        SELECT tenant_id, name
        FROM roles
        ORDER BY tenant_id, name;
    """,
    "permissions": """
        SELECT code
        FROM permissions
        ORDER BY code;
    """,
    "tenant_user_roles": """
        SELECT tenant_id, user_id, role_id
        FROM tenant_user_roles
        ORDER BY tenant_id, user_id, role_id;
    """,
    "role_permissions_count": """
        SELECT COUNT(*)
        FROM role_permissions;
    """,
}

with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        for name, sql in queries.items():
            print(f"\n--- {name} ---")
            cur.execute(sql)
            rows = cur.fetchall()
            for row in rows:
                print(row)
