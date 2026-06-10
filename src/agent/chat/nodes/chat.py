from langchain.messages import AIMessage, SystemMessage, ToolMessage
from langchain_classic.schema import BaseMessage
from langgraph.func import END
from src.agent.chat.config import ChatState
from src.llm import init_model
from src.tools import knowledge_search, read_file, save_to_knowledge
from src.tools.human_review import request_human_review
from src.tools.research import research

# 需要确认的工具白名单
TOOLS_REQUIRING_CONFIRM = {"research", "save_to_knowledge"}

CHAT_SYSTEM_PROMPT = """
你是一个知识助手。你可以：
1. 直接回答用户的简单问题（闲聊、解释概念、提供建议）
2. 调用 knowledge_search 检索已有知识库
3. 当用户需要深度研究时，调用 research 工具
4. 调用 read_file 读取用户上传的附件内容
5. 调用 save_to_knowledge 将内容存入知识库

规则：
- 当工具需要人工确认时，先调用request_human_review工具，进行人工确认，以下工具需要确认：{tools}
- 当用户要求输出流程图或者你认为输出内容比较适合流程图展示的时候，可以用```mermaid 和 ```包裹的代码块，其中要求输出mermaid库的输出格式
- 用户消息附带附件时，必须先调用 read_file 获取文件内容，然后根据用户意图处理
- 根据用户意图决定是否调用 save_to_knowledge
- 用户说"存入知识库"、"记录下来"、"保存一下"等类似意图时，调用 save_to_knowledge
- 对于非简单问题，优先调用 knowledge_search 查看是否有相关知识
- knowledge_search 有结果时，结合检索结果回答，无需再 research
- knowledge_search 无结果且需要深度研究时，再调用 research
- 触发 research 的场景：用户要求总结、分析、深度研究某个话题；用户消息以 /research 开头；需要搜索多个来源并综合分析

回复使用中文。
""".format(tools="，".join(TOOLS_REQUIRING_CONFIRM))


async def chat_node(state: ChatState) -> dict:
    llm = init_model()
    llm_with_tools = llm.bind_tools([research, knowledge_search, read_file, save_to_knowledge, request_human_review])

    state_messages = state.get("messages", [])
    existing_messages = []

    for msg in state_messages:
        if isinstance(msg, SystemMessage):
            continue
        existing_messages.append(msg)

    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)] + existing_messages
    messages = _sanitize_messages(messages)

    response = await llm_with_tools.ainvoke(messages)
    return {
        "messages": [response],
    }

def route_chat_node(state: ChatState) -> str:
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return END
    
    tool_names = [tc["name"] for tc in last_message.tool_calls]

    needs_confirm = any(name in TOOLS_REQUIRING_CONFIRM for name in tool_names)
    if "request_human_review" in tool_names or needs_confirm:
        return "human"
    return "tools"

def _sanitize_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """修复孤立 tool_calls：为没有对应 ToolMessage 的 tool_call 补占位响应"""
    result: list[BaseMessage] = []
    for i, msg in enumerate(messages):
        result.append(msg)
        if isinstance(msg, AIMessage) and msg.tool_calls:
            # 收集后续所有 ToolMessage 的 tool_call_id
            following_tool_ids = {
                m.tool_call_id for m in messages[i + 1:] if isinstance(m, ToolMessage)
            }
            # 为缺少 ToolMessage 的 tool_call 补占位
            for tc in msg.tool_calls:
                if tc["id"] not in following_tool_ids:
                    result.append(ToolMessage(
                        content="[工具执行结果未记录]",
                        tool_call_id=tc["id"]
                    ))
    return result