from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.func import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.chat.config import ChatState
from src.agent.chat.nodes.chat import chat_node, route_chat_node
from src.agent.chat.nodes.human import human_node
from src.tools import research, knowledge_search, read_file, save_to_knowledge


def _build_chat_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(ChatState)
    builder.add_node("chat", chat_node)
    builder.add_node("human", human_node)
    builder.add_node("tools", ToolNode([research, knowledge_search, read_file, save_to_knowledge]))

    builder.add_edge(START, "chat")
    builder.add_edge("tools", "chat")
    builder.add_edge("human", "chat")

    builder.add_conditional_edges(
        "chat",
        route_chat_node,
        {
            "tools": "tools",
            "human": "human",
            END: END,
        },
    )

    graph = builder.compile(checkpointer=checkpointer)

    return graph


def create_chat_agent(checkpointer: AsyncPostgresSaver):
    return _build_chat_graph(checkpointer=checkpointer)
