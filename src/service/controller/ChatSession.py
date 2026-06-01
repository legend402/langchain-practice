from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.db import ChatSession

async def create_session(session: AsyncSession, thread_id: str, title: str, user_id: UUID):
  session.add(
    ChatSession(
      thread_id=thread_id,
      title=title,
      user_id=user_id,
    )
  )
  await session.commit()
