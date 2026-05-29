from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.db import ChatMessage

async def create_message(session: AsyncSession, thread_id: str, role: str, content: str, node_name: Optional[str] = None, state: Optional[dict] = None):
  session.add(
    ChatMessage(
      thread_id=thread_id,
      role=role,
      node_name=node_name,
      content=content,
      state=state,
    )
  )
  await session.commit()
  
async def get_messages(session: AsyncSession, thread_id: str):
  result = await session.exec(
    select(ChatMessage).where(ChatMessage.thread_id == thread_id).order_by(ChatMessage.create_at)
  )

  return result.all()
