from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.db import ChatSession

async def create_session(session: AsyncSession, thread_id: str, title: str):
  session.add(
    ChatSession(
      thread_id=thread_id,
      title=title,
    )
  )
  await session.commit()
