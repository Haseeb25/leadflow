import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/leadflow")

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class Lead(Base):
    __tablename__ = "leads"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(500))
    url         = Column(String(1000), unique=True, index=True)
    description = Column(Text)
    source_url  = Column(String(1000))
    score       = Column(Integer, default=0)       # quality score 0-100
    processed   = Column(Boolean, default=False)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id            = Column(Integer, primary_key=True)
    status        = Column(String(50))             # running, done, failed
    records_found = Column(Integer, default=0)
    errors        = Column(Integer, default=0)
    started_at    = Column(DateTime, server_default=func.now())
    finished_at   = Column(DateTime, nullable=True)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
