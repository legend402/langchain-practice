from langchain.messages import SystemMessage
from src.agent.chat.config import ChatState
from src.llm import init_model
from src.tools.research import research

CHAT_SYSTEM_PROMPT = """你是一个知识助手。你可以：
1. 直接回答用户的简单问题（闲聊、解释概念、提供建议）
2. 当用户需要深度研究时，调用 research 工具

触发 research 的场景：
- 用户要求总结、分析、深度研究某个话题
- 用户消息以 /research 开头（必须调用）
- 需要搜索多个来源并综合分析

不触发 research 的场景：
- 简单问答、闲聊、已有知识的解释

当 research 工具返回结果后：
- 如果结果质量 OK，基于结果生成最终回复
- 如果结果不完整或有误，可以再次调用 research 或补充说明

回复使用中文。"""


async def chat_node(state: ChatState) -> dict:
    llm = init_model()
    llm_with_tools = llm.bind_tools([research])

    state_messages = state.get("messages", [])
    existing_messages = []

    for msg in state_messages:
        if isinstance(msg, SystemMessage):
            continue
        existing_messages.append(msg)

    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)] + existing_messages

    response = await llm_with_tools.ainvoke(messages)
    return {
        "messages": [response],
    }
