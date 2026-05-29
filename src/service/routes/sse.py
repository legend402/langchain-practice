import asyncio
import json
from typing import Any
from asyncio import Task

from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import AgentState

type AgentType = CompiledStateGraph[AgentState, None, AgentState, AgentState]

async def event_generator(
    agent: AgentType,
    initial_state: Any,
    session_id: str,
    engine: AsyncEngine,
    sessions: dict,
    create_message_fn,
):
    task = asyncio.current_task()
    sessions[session_id] = task
    config = {"configurable": {"thread_id": session_id}}
    try:
        async for mode, state in agent.astream(
            initial_state, config, stream_mode=["updates", "custom"]
        ):
            if mode == "custom":
                state["session_id"] = session_id
                yield f"data: {json.dumps(state)}\n\n"
                continue

            if "__interrupt__" in state:
                interrupt_state = {
                    "human": state["__interrupt__"][0].value,
                    "session_id": session_id,
                }
                yield f"data: {json.dumps(interrupt_state)}\n\n"
                continue

            node = list(state.keys())[0] if state else None
            state["session_id"] = session_id
            if "messages" in state[node]:
                del state[node]["messages"]
            async with AsyncSession(engine) as db:
                await create_message_fn(
                    session=db,
                    thread_id=session_id,
                    role="AI",
                    node_name=node,
                    content="",
                    state=state,
                )
                await db.commit()
            yield f"data: {json.dumps(state)}\n\n"
    except asyncio.CancelledError:
        yield f"data: {json.dumps({'type': 'stopped', 'session_id': session_id})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'session_id': session_id, 'error': str(e)})}\n\n"
    finally:
        sessions.pop(session_id, None)
