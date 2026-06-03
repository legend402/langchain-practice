import os
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from src.service.db.db import ChatMessage, ChatSession, FileUpload, KnowledgeEntry

def create_engine(db_uri: str) -> AsyncEngine:
  async_uri = db_uri.replace("postgresql://", "postgresql+asyncpg://")
  return create_async_engine(async_uri, echo=False)

async def init_db(engine):
  async with engine.begin() as conn:
    await conn.run_sync(SQLModel.metadata.create_all)

engine = create_engine(os.getenv("PGSQL_DB_URI"))
session_marker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
  async with AsyncSession(engine) as session:
    yield session
