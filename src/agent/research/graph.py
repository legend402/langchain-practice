from typing import Optional
from langgraph.func import END, START
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph

from src.config import AgentState
from src.agent.research.nodes import (
    supervisor_node,
    search_node,
    read_node,
    analyze_node,
    tag_node,
    knowledge_node,
    reviewer_node,
    human_gate_node,
    finalize_node,
    route_supervisor_node,
    route_review_node,
    route_human_gate_node,
)


def _build_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("search", search_node)
    builder.add_node("read", read_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("tag", tag_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("review", reviewer_node)
    builder.add_node("human", human_gate_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("search", "supervisor")
    builder.add_edge("read", "supervisor")
    builder.add_edge("analyze", "supervisor")
    builder.add_edge("tag", "supervisor")
    builder.add_edge("knowledge", "supervisor")
    builder.add_edge("finalize", END)

    builder.add_conditional_edges(
        "supervisor",
        route_supervisor_node,
        {
            "search": "search",
            "read": "read",
            "analyze": "analyze",
            "tag": "tag",
            "knowledge": "knowledge",
            "review": "review",
            "finalize": "finalize",
            "human": "human",
        },
    )

    builder.add_conditional_edges(
        "review",
        route_review_node,
        {
            "replan": "supervisor",
            "pass": "finalize",
            "need_human": "human",
        },
    )

    builder.add_conditional_edges(
        "human",
        route_human_gate_node,
        {
            "approved": "finalize",
            "revise": "supervisor",
            "extra_input": "supervisor",
        },
    )

    return builder.compile(checkpointer=checkpointer)


def _build_graph_without_db():
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("search", search_node)
    builder.add_node("read", read_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("tag", tag_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("review", reviewer_node)
    builder.add_node("human", human_gate_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("search", "supervisor")
    builder.add_edge("read", "supervisor")
    builder.add_edge("analyze", "supervisor")
    builder.add_edge("tag", "supervisor")
    builder.add_edge("knowledge", "supervisor")
    builder.add_edge("finalize", END)

    builder.add_conditional_edges(
        "supervisor",
        route_supervisor_node,
        {
            "search": "search",
            "read": "read",
            "analyze": "analyze",
            "tag": "tag",
            "knowledge": "knowledge",
            "review": "review",
            "finalize": "finalize",
            "human": "human",
        },
    )

    builder.add_conditional_edges(
        "review",
        route_review_node,
        {
            "replan": "supervisor",
            "pass": "finalize",
            "need_human": "human",
        },
    )

    builder.add_conditional_edges(
        "human",
        route_human_gate_node,
        {
            "approved": "finalize",
            "revise": "supervisor",
            "extra_input": "supervisor",
        },
    )

    return builder.compile()


def create_research_agent(
    checkpointer: Optional[AsyncPostgresSaver] = None,
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    return _build_graph_without_db() if not checkpointer else _build_graph(checkpointer)
