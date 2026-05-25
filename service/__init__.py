import json
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langgraph.types import Command

from graph import build_graph_agent
from utils import get_initial_state

load_dotenv()

class ChatStart(BaseModel):
  query: str
  
class ChatFeedback(BaseModel):
  decision:str
  comment: str
  additional_material: str | None = None

def create_agent_service():
  app = FastAPI()
  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )
  agent = build_graph_agent()

  @app.post("/chat/start")
  async def chat_start(body: ChatStart):
    initial_state = get_initial_state({
      "user_query": body.query
    })
    thread_id = str(uuid4())
    config = { "configurable": { "thread_id": thread_id } }

    async def event_generator():
      async for _, state in agent.astream(initial_state, config, stream_mode=["updates", "custom"]):
        if "__interrupt__" in state:
          interrupt_state = { "human": state["__interrupt__"][0].value, "session_id": thread_id }
          yield f"data: {json.dumps(interrupt_state)}\n\n"
          continue

        state["session_id"] = thread_id
        yield f"data: {json.dumps(state)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/events-stream")
  

  @app.post("/chat/{session_id}/feedback")
  async def chat_restore(session_id: str, body: ChatFeedback):
    config = { "configurable": { "thread_id": session_id } }

    async def event_generator():
      async for _, state in agent.astream(Command(resume=body.model_dump()), config, stream_mode=["updates", "custom"]):
        if "__interrupt__" in state:
          interrupt_state = { "human": state["__interrupt__"][0].value, "session_id": session_id }
          yield f"data: {json.dumps(interrupt_state)}\n\n"
          continue

        state["session_id"] = session_id
        yield f"data: {json.dumps(state)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/events-stream")

  return app

app = create_agent_service()
