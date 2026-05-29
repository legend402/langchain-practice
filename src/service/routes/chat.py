from typing import Any, Optional
from uuid import uuid4
from asyncio import Task

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, delete

from src.service.controller.ChatMessage import create_message, get_messages
from src.service.controller.ChatSession import create_session
from src.service.db.database import get_session, engine
from src.service.db.db import ChatSession, ChatMessage
from src.service.result import Result
from src.service.routes.sse import event_generator
from src.utils.agent import get_initial_state, recover_state

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatStart(BaseModel):
    query: str
    thread_id: Optional[str] = None

class ChatFeedback(BaseModel):
    decision: str
    comment: str
    additional_material: str | None = None

@router.get("/sessions")
async def chat_sessions(session: AsyncSession = Depends(get_session)):
    result = await session.exec(
        select(ChatSession).order_by(ChatSession.create_at.desc())
    )
    return Result.success(result.all())

@router.delete("/{id}")
async def delete_sessions(id: str, session: AsyncSession = Depends(get_session)):
    result = await session.get(ChatSession, id)
    if not result:
        return Result.error(f"未找到id为{id}的数据")
    await session.exec(delete(ChatMessage).where(ChatMessage.thread_id == id))
    await session.delete(result)
    await session.commit()
    return Result.success(message="删除成功")

@router.get("/{thread_id}/messages")
async def chat_messages(thread_id: str, session: AsyncSession = Depends(get_session)):
    list_ = await get_messages(session, thread_id)
    return Result.success(list_)

@router.post("/start")
async def chat_start(body: ChatStart, session: AsyncSession = Depends(get_session)):
    from src.service import get_app

    app = get_app()
    agent = app.state.agent
    thread_id = body.thread_id or str(uuid4())

    state = {"user_query": body.query}
    # 如果没有会话记录，就创建新的记录
    if body.thread_id is None:
        await create_session(session=session, thread_id=thread_id, title=body.query[:50])
    # 如果存在记录，就获取完整的记录，然后重新把记录传回get_initial_state，恢复上下文
    elif session.get(ChatSession, thread_id):
        messages = await get_messages(session, thread_id)
        state = recover_state(messages)
        state["messages"] = state["messages"] + [("human", body.query)]

    await create_message(
        session=session, thread_id=thread_id, role="human", content=body.query
    )
    await session.commit()

    initial_state = get_initial_state(state)

    return StreamingResponse(
        event_generator(
            agent=agent,
            initial_state=initial_state,
            session_id=thread_id,
            engine=engine,
            sessions=app.state.sessions,
            create_message_fn=create_message,
        ),
        media_type="text/events-stream",
    )

@router.post("/{thread_id}/stop")
async def chat_stop(thread_id: str):
    from src.service import get_app

    app = get_app()
    task: Task[Any] = app.state.sessions.get(thread_id)
    if task and not task.done():
        task.cancel()
        return Result.success(message="已停止")
    return Result.success(message="未找到正在运行中的任务")

@router.post("/{session_id}/feedback")
async def chat_feedback(session_id: str, body: ChatFeedback):
    from src.service import get_app
    from langgraph.types import Command

    app = get_app()
    agent = app.state.agent

    return StreamingResponse(
        event_generator(
            agent=agent,
            initial_state=Command(resume=body.model_dump()),
            session_id=session_id,
            engine=engine,
            sessions=app.state.sessions,
            create_message_fn=create_message,
        ),
        media_type="text/events-stream",
    )
