import json
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
import os

from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from config import AgentState
from graph import _build_graph
from service.controller.ChatMessage import create_message
from service.controller.ChatSession import create_session
from service.db.database import engine, get_session, init_db, ChatSession
from service.db.db import ChatMessage, Roles
from service.result import Result
from utils import get_initial_state

load_dotenv()

DB_URI = os.getenv("PGSQL_DB_URI")

type AgentType = CompiledStateGraph[AgentState, None, AgentState, AgentState]

class ChatStart(BaseModel):
  query: str
  
class ChatFeedback(BaseModel):
  decision:str
  comment: str
  additional_material: str | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
  pool = AsyncConnectionPool(DB_URI, min_size=2, max_size=10, kwargs={"autocommit": True}, open=False)
  await pool.open()
  checkpointer = AsyncPostgresSaver(pool)
  await checkpointer.setup()
  app.state.agent = _build_graph(checkpointer)
  
  await init_db(engine)
  app.state.engine = engine
  yield
  await pool.close()

def create_agent_service():
  app = FastAPI(lifespan=lifespan)
  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )
  
  @app.get('/chat/sessions')
  async def chat_sessions(session: AsyncSession = Depends(get_session)):
    result = await session.exec(
      select(ChatSession).order_by(ChatSession.create_at.desc())
    )

    return Result.success(result.all())
  
  @app.delete('/chat/{id}')
  async def delete_sessions(id: str, session: AsyncSession = Depends(get_session)):
    result = await session.get(ChatSession, id)
    
    if not result:
      return Result.error(f"未找到id为{id}的数据")

    await session.delete(result)
    await session.commit()
    
    return Result.success(message="删除成功")
  
  @app.get('/chat/{thread_id}/messages')
  async def chat_sessions(thread_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.exec(
      select(ChatMessage).where(ChatMessage.thread_id == thread_id)
    )

    return Result.success(result.all())

  @app.post("/chat/start")
  async def chat_start(body: ChatStart, session: AsyncSession = Depends(get_session)):
    agent = app.state.agent
    initial_state = get_initial_state({
      "user_query": body.query
    })
    thread_id = str(uuid4())
    await create_session(session=session, thread_id=thread_id, title=body.query[:50])
    await create_message(session=session, thread_id=thread_id, role="human", content=body.query)

    return StreamingResponse(event_generator(agent, initial_state, session, thread_id), media_type="text/events-stream")
  

  @app.post("/chat/{session_id}/feedback")
  async def chat_restore(session_id: str, body: ChatFeedback, session: AsyncSession = Depends(get_session)):
    agent = app.state.agent

    return StreamingResponse(event_generator(agent, Command(resume=body.model_dump()), session, session_id), media_type="text/events-stream")

  async def event_generator(agent: AgentType, initial_state: Any, session: AsyncSession, session_id: str):
    config = { "configurable": { "thread_id": session_id } }
    async for _, state in agent.astream(initial_state, config, stream_mode=["updates", "custom"]):
      if "__interrupt__" in state:
        interrupt_state = { "human": state["__interrupt__"][0].value, "session_id": session_id }
        yield f"data: {json.dumps(interrupt_state)}\n\n"
        continue
      print(state)
      node = list(state.keys())[0] if state else None

      state["session_id"] = session_id
      if "messages" in state: del state["messages"]
      await create_message(session=session, thread_id=session_id, role="AI", node_name=node, content="", state=state)
      yield f"data: {json.dumps(state)}\n\n"

  return app

app = create_agent_service()
