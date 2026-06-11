import asyncio
import json
from typing import Any

from langchain.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import AgentState

AgentType = CompiledStateGraph[AgentState, None, AgentState, AgentState]


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
            initial_state, config, stream_mode=["updates", "custom", "messages"]
        ):
            if state is not None and isinstance(state, dict) and "__interrupt__" in state:
                interrupt_state = {
                    "human": state["__interrupt__"][0].value,
                    "session_id": session_id,
                }
                yield f"data: {json.dumps(interrupt_state)}\n\n"
                continue
            if mode == "messages":
                token, metadata = state
                node = metadata.get("langgraph_node", "chat")
                if node != "chat": continue
                if isinstance(token, AIMessageChunk) and token.content:
                    event = {
                        "stream_chunk": {
                            "chunk": token.content,
                            "node_output_key": node,
                        }
                    }
                    yield f"data: {json.dumps(event)}\n\n"
                continue
            if mode == "custom":
                if "research" == state.get("source"):
                    if "node_update" == state.get("type"):
                        node = state.get("node")
                        node_state = state.get("state", {})
                        async with AsyncSession(engine) as db:
                            await create_message_fn(
                                session=db,
                                thread_id=session_id,
                                role="ai",
                                node_name=node,
                                content="",
                                state=node_state,
                            )
                            await db.commit()
                    state["session_id"] = session_id
                    yield f"data: {json.dumps(state)}\n\n"
                continue


            if "updates" == mode:
                if not state:
                    continue

                node = list(state.keys())[0] if state else None
                node_data = state.get(node, {})
                content = ""
                if "messages" in node_data:
                    content = node_data["messages"][-1].content
                    del node_data["messages"]

                state["session_id"] = session_id
                async with AsyncSession(engine) as db:
                    await create_message_fn(
                        session=db,
                        thread_id=session_id,
                        role="ai",
                        node_name=node,
                        content=content,
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
