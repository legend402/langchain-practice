import json
from langchain.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.types import interrupt
from src.agent.chat.config import ChatState
from src.agent.chat.nodes.chat import TOOLS_MAP, TOOLS_REQUIRING_CONFIRM
from src.llm import init_model

HUMAN_SYSTEM_PROMPT = """
你是一个决策辅助助手。根据对话上下文，生成结构化的人工干预请求。

你必须输出以下 JSON 格式（不要输出其他内容）：

## 类型说明

### confirm — 确认操作
当需要用户确认某个操作是否执行时使用。
- title: 确认事项的简短标题
- description: 详细说明该操作的目的和影响

只输出 JSON：
示例：
{
  "type": "confirm",
  "items": [
    {"title": "将内容存入知识库", "description": "检测到当前对话内容适合存入知识库，是否执行？"}
  ]
}

### choose — 方案选择
当存在多种可行方案需要用户选择时使用。
- title: 选择事项的标题
- description: 背景描述
- options: 可选方案列表，每个方案有 label 和 description

只输出 JSON：
示例：
{
  "type": "choose",
  "items": [
    {
      "title": "选择研究方式",
      "description": "有两种方式可以完成你的需求",
      "options": [
        {"label": "快速搜索", "description": "使用 Tavily 快速搜索，耗时短，结果较简略"},
        {"label": "深度研究", "description": "多轮搜索+综合分析，耗时长，结果更全面"}
      ]
    }
  ]
}

### question_list — 多项确认
当有多个问题需要用户逐一确认时使用。
- 每个 item 必须恰好有 3 个 options
- 每个 item 有 title 和 description

只输出 JSON：
示例：
{
  "type": "question_list",
  "items": [
    {
      "title": "存储位置",
      "description": "选择知识库的存储分类",
      "options": [
        {"label": "技术文档", "description": "归入技术类知识库"},
        {"label": "项目笔记", "description": "归入项目相关笔记"},
        {"label": "通用知识", "description": "归入通用知识库"}
      ]
    }
  ]
}
"""


async def human_node(state: ChatState) -> dict:
    state_messages = state.get("messages", [])
    last_msg = state_messages[-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []

    if not tool_calls:
        return {"messages": [AIMessage(content="没有待确认的工具调用")]}

    # 分离两类 tool_calls
    review_tc = next(
        (tc for tc in tool_calls if tc["name"] == "request_human_review"), None
    )
    confirm_tcs = [tc for tc in tool_calls if tc["name"] in TOOLS_REQUIRING_CONFIRM]
    other_tcs = [
        tc
        for tc in tool_calls
        if tc["name"] not in TOOLS_REQUIRING_CONFIRM
        and tc["name"] != "request_human_review"
    ]

    # ===== 路径 A: LLM 主动调了 request_human_review =====
    # 场景：LLM 判断需要用户做 choose / question_list 决策
    if review_tc:
        llm = init_model()
        messages = [
            SystemMessage(content=HUMAN_SYSTEM_PROMPT),
            AIMessage(content=json.dumps(tool_calls[0]["args"])),
        ]
        chain = llm | JsonOutputParser()
        response = await chain.ainvoke(messages)

        feedback = interrupt(response)
        summary = _build_feedback_summary(response, feedback)

        result_messages = [ToolMessage(content=summary, tool_call_id=review_tc["id"])]
        # other_tcs 补占位（LLM 决策后可能改策略，这些工具不需要执行）
        for tc in other_tcs:
            result_messages.append(
                ToolMessage(content="[等待用户决策后重新确认]", tool_call_id=tc["id"])
            )
        return result_messages

    # ===== 路径 B: 架构层拦截白名单工具 =====
    # 场景：LLM 直接调了需要授权的工具
    if len(confirm_tcs):
        confirm_request = _build_confirm_request(confirm_tcs)
        feedback = interrupt(confirm_request)

        result_messages = []

        if feedback["items"][0].get("confirmed", False):
            for tc in confirm_tcs:
                try:
                    result = await TOOLS_MAP[tc["name"]].ainvoke(input=tc["args"])
                    result_messages.append(
                        ToolMessage(content=result, tool_call_id=tc["id"])
                    )
                except Exception as e:
                    result_messages.append(
                        ToolMessage(content=f"工具执行失败：{e}", tool_call_id=tc["id"])
                    )
        else:
            for tc in confirm_tcs:
                result_messages.append(
                    ToolMessage(content=f"用户取消了此操作：{e}", tool_call_id=tc["id"])
                )

        for tc in other_tcs:
            try:
                result = await TOOLS_MAP[tc["name"]](**tc["args"])
                result_messages.append(
                    ToolMessage(content=result, tool_call_id=tc["id"])
                )
            except Exception as e:
                result_messages.append(
                    ToolMessage(content=f"工具执行失败：{e}", tool_call_id=tc["id"])
                )
        return {"messages": result_messages}

    return {"messages": [AIMessage(content="没有需要处理的工具调用")]}


# 工具参数 → confirm 请求的映射
TOOL_CONFIRM_TEMPLATES = {
    "knowledge_search": "搜索知识库中关于「{query}」的内容",
    "research": "对「{user_query}」进行深度研究",
    "save_to_knowledge": "将「{title}」存入知识库",
}


def _build_confirm_request(tool_calls: list) -> dict:
    """从工具调用参数直接构建 confirm 请求"""
    items = []
    for tc in tool_calls:
        template = TOOL_CONFIRM_TEMPLATES.get(tc["name"], "执行 {name}")
        desc = template.format(**tc["args"], name=tc["name"])
        items.append(
            {
                "title": "确定执行工具调用",
                "description": desc,
            }
        )
    return {"type": "confirm", "items": items}


def _build_feedback_summary(response, feedback):
    # 先拼接原始问题上下文（让 LLM 知道有哪些选项）
    question_answer = json.dumps(response, ensure_ascii=False, indent=2)

    # 拼接用户的选择结果
    parts = []
    for answer in feedback["items"]:
        idx = answer["item_index"]
        item = response["items"][idx]
        title = item["title"]

        if feedback["type"] == "confirm":
            decision = "确认" if answer.get("confirmed") else "取消"
            line = f"【{title}】用户{decision}"
        else:
            opt_idx = answer.get("selected_option_index")
            if opt_idx is not None:
                label = item["options"][opt_idx]["label"]
                line = f"【{title}】用户{label}"
            else:
                line = f"【{title}】用户未选择预设选项"
        comment = answer.get("comment")
        if comment:
            line += f"，补充说明：{comment}"
        parts.append(line)

    # 组合：原始问题 + 用户反馈
    return f"原始问题： \n{question_answer}\n\n用户反馈结果：\n" + "\n".join(parts)
