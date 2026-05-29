import warnings
from contextlib import asynccontextmanager

import langchain_core._api.deprecation
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

import os

from src.graph import _build_graph
from src.service.db.database import engine, init_db
from src.service.routes.chat import router as chat_router

load_dotenv()

warnings.filterwarnings("ignore", message=".*allowed_objects.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langgraph")

DB_URI = os.getenv("PGSQL_DB_URI")

_app: FastAPI | None = None

def get_app() -> FastAPI:
    return _app

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _app
    pool = AsyncConnectionPool(
        DB_URI, min_size=2, max_size=10, kwargs={"autocommit": True}, open=False
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    app.state.agent = _build_graph(checkpointer)
    await init_db(engine)
    app.state.engine = engine
    app.state.sessions = {}
    _app = app
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
    app.include_router(chat_router)
    return app

app = create_agent_service()
