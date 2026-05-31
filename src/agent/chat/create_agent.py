from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.func import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent.chat.config import ChatState
from src.agent.chat.nodes.chat import chat_node
from src.tools.research import research


def _build_chat_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(ChatState)
    builder.add_node("chat", chat_node)
    builder.add_node("tools", ToolNode([research]))

    builder.add_edge(START, "chat")
    builder.add_edge("tools", "chat")

    builder.add_conditional_edges(
        "chat",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    graph = builder.compile(checkpointer=checkpointer)

    return graph


def create_chat_agent(checkpointer: AsyncPostgresSaver):
    return _build_chat_graph(checkpointer=checkpointer)
