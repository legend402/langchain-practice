from typing import Annotated, Optional, TypedDict

from langchain.messages import HumanMessage
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str
    research_result: Optional[str]
    research_active: bool


def get_initial_chat_state(state: ChatState):
    initial_state: ChatState = {
        "user_query": state.get("user_query", ""),
        "messages": (
            state["messages"]
            if state.get("messages", None)
            else (
                [HumanMessage(state.get("user_query"))]
                if state.get("user_query")
                else []
            )
        ),
        "research_active": state.get("research_active", False),
        "research_result": state.get("research_result", ""),
    }
    return initial_state


def recover_chat_state(messages: list) -> "ChatState":
    from langchain_core.messages import HumanMessage, AIMessage

    state: ChatState = {"messages": []}
    for message in messages:
        if message.role == "human":
            state["messages"].append(HumanMessage(content=message.content))
        else:
            state["messages"].append(AIMessage(content=message.content or ""))
    return state
