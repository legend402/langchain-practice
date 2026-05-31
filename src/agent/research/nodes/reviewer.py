from src.config import AgentState
from src.utils import node_hook
from src.utils.agent import get_state_message
from src.agent.research.nodes._base import create_structure_node

reviewer_prompt = """
你是 reviewer_worker，负责审核知识点总结是否可以进入最终输出。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

分析摘要：
{analysis_summary}

知识点总结：
{knowledge_summary}

标签：
{tags}

来源索引：
{source_index}

你需要检查：

1. 是否回答了用户问题。
2. 是否覆盖核心知识点。
3. 结构是否清晰。
4. 是否存在明显事实错误。
5. 是否存在没有依据的结论。
6. 是否保留了必要的不确定性。
7. tags 是否合理。
8. sources 是否足够支撑总结。
9. 是否需要补充搜索、重新阅读、重新分析、重新打标签或重新生成。
10. 是否存在必须由用户确认的问题。

审核结果只能是：

- pass：可以进入 finalize。
- replan：系统可以自行修复，应回到 supervisor。
- need_human：必须由用户确认，应进入 human_gate。

如果选择 replan，请给出 next_action_hint：
search、read、analyze、tag、knowledge 之一。

只输出 JSON：

{{
  "review_result": {{
    "status": "pass | replan | need_human",
    "issues": ["问题"],
    "suggestions": ["建议"],
    "next_action_hint": "search | read | analyze | tag | knowledge | null",
    "need_human_reason": "需要人工确认的原因或 null",
    "confidence": 0.0
  }},
  "trace": ["reviewer_worker completed"]
}}
"""


def reviewer_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "analysis_summary": state.get("analysis_summary"),
        "knowledge_summary": state.get("knowledge_summary"),
        "tags": state.get("tags"),
        "source_index": state.get("source_index", []),
    }


@node_hook()
async def reviewer_node(state: AgentState):
    result = await create_structure_node(state, reviewer_prompt, reviewer_input)
    result["messages"] = state["messages"] + [
        ("ai", get_state_message("review", result))
    ]
    return result


def route_review_node(state: AgentState):
    """审核路由"""
    return state["review_result"]["status"]
