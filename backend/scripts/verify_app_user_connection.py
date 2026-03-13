import asyncio
import asyncpg

DSN = "postgresql://app_user:AppUser_Strong_Password_123@127.0.0.1:5432/supacrm"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        user = await conn.fetchval("select current_user")
        db = await conn.fetchval("select current_database()")
        print("Connected as:", user)
        print("Database:", db)
    finally:
        await conn.close()

asyncio.run(main())
