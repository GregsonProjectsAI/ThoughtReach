from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# ssl=False: local Docker Postgres does not support SSL; asyncpg's SSL handshake
# causes WinError 64 (ConnectionResetError) which hangs requests indefinitely on Windows.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"ssl": False}
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
