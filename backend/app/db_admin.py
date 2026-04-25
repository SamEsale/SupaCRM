from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

admin_engine = create_async_engine(
    settings.DATABASE_URL_ADMIN_ASYNC,
    pool_pre_ping=True,
)

AdminSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=admin_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_admin_session() -> AsyncSession:
    async with AdminSessionLocal() as session:
        yield session
