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

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from config import AgentState
from graph import _build_graph
from service.db.database import engine, get_session, init_db, ChatSession
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
  pool = AsyncConnectionPool(DB_URI, min_size=2, max_size=10, kwargs={"autocommit": True})
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
  
  @app.get('/chat/create')
  async def chat_sessions(session: AsyncSession = Depends(get_session)):
    result = await session.exec(
      select(ChatSession).order_by(ChatSession.create_at.desc())
    )

    return Result.success(result.all())

  @app.post("/chat/start")
  async def chat_start(body: ChatStart, session: AsyncSession = Depends(get_session)):
    agent = app.state.agent
    initial_state = get_initial_state({
      "user_query": body.query
    })
    thread_id = str(uuid4())
    await session.add(
      ChatSession(
        thread_id=thread_id,
        title=body.query,
      )
    )
    session.commit()

    return StreamingResponse(event_generator(agent, initial_state, thread_id), media_type="text/events-stream")
  

  @app.post("/chat/{session_id}/feedback")
  async def chat_restore(session_id: str, body: ChatFeedback):
    agent = app.state.agent

    return StreamingResponse(event_generator(agent, Command(resume=body.model_dump()), session_id), media_type="text/events-stream")

  async def event_generator(agent: AgentType, initial_state: Any, session_id: str):
    config = { "configurable": { "thread_id": session_id } }
    async for _, state in agent.astream(initial_state, config, stream_mode=["updates", "custom"]):
      if "__interrupt__" in state:
        interrupt_state = { "human": state["__interrupt__"][0].value, "session_id": session_id }
        yield f"data: {json.dumps(interrupt_state)}\n\n"
        continue

      state["session_id"] = session_id
      if "messages" in state: del state["messages"]
      yield f"data: {json.dumps(state)}\n\n"

  return app

app = create_agent_service()
