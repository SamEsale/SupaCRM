import asyncio
import asyncpg

DSN = "postgresql://app_user:AppUser_Strong_Password_123@127.0.0.1:5432/supacrm"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 1) Set tenant to tenant-demo and read rows (should return only tenant-demo rows)
        await conn.execute("select set_config('app.tenant_id', 'tenant-demo', true)")
        rows = await conn.fetch("select tenant_id, action from public.audit_logs order by created_at desc limit 5")
        print("Top rows under tenant-demo context:")
        for r in rows:
            print(dict(r))

        # 2) Set tenant to dev-tenant, then attempt to INSERT tenant-demo (should FAIL)
        await conn.execute("select set_config('app.tenant_id', 'dev-tenant', true)")
        try:
            await conn.execute("""
                insert into public.audit_logs (tenant_id, action, resource, message, status_code)
                values ('tenant-demo','rls.test','system','THIS SHOULD FAIL',200)
            """)
            print("UNEXPECTED: insert succeeded (this would be a security failure)")
        except Exception as e:
            print("Expected failure on cross-tenant insert:")
            print(type(e).__name__, str(e))

        # 3) Insert matching tenant (should succeed)
        await conn.execute("select set_config('app.tenant_id', 'tenant-demo', true)")
        await conn.execute("""
            insert into public.audit_logs (tenant_id, action, resource, message, status_code)
            values ('tenant-demo','rls.test','system','insert allowed',200)
        """)
        print("PASS: insert allowed for matching tenant")

    finally:
        await conn.close()

asyncio.run(main())
