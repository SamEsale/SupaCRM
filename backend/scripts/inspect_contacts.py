import asyncio
from sqlalchemy import text

from app.db import async_session_factory


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'contacts'
                ORDER BY ordinal_position
                """
            )
        )

        print("== contacts columns ==")
        for row in result:
            print(row)


if __name__ == "__main__":
    asyncio.run(main())