from langgraph.types import interrupt

from src.config import AgentState
from src.utils import node_hook
from src.utils.agent import get_state_message
from src.nodes._base import create_structure_node

human_gate_prompt = """
你是 human_gate，负责在 Agent 无法自行判断时向用户请求确认或补充信息。

用户问题：
{user_query}

任务目标：
{task_goal}

当前知识点总结：
{knowledge_summary}

审核结果：
{review_result}

历史人工反馈：
{human_feedback}

你的任务：

1. 判断为什么需要人工介入。
2. 简要说明当前已经完成什么。
3. 明确指出需要用户确认的问题。
4. 提供清晰的回复格式。
5. 优先提出 1 到 3 个关键问题。

不要继续分析。
不要生成最终答案。
不要替用户做无法确认的选择。

只输出 JSON：

{{
  "human_message": "展示给用户的问题说明",
  "expected_reply_schema": {{
    "decision": "approved | revise | extra_input",
    "comment": "string",
    "additional_material": "string | null"
  }},
  "trace": ["human_gate waiting for user input"]
}}
"""

def human_gate_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "knowledge_summary": state.get("knowledge_summary"),
        "review_result": state.get("review_result"),
        "human_feedback": state.get("human_feedback"),
    }

@node_hook()
def human_gate_node(state: AgentState):
    result = create_structure_node(state, human_gate_prompt, human_gate_input)
    result["messages"] = state["messages"] + [("AI", get_state_message("human", result))]
    feedback = interrupt({
        "human_message": result.get("human_message", ""),
        "expected_reply_schema": result.get("expected_reply_schema", {}),
    })
    result["human_feedback"] = feedback
    result["messages"].append(("human", get_state_message("human", result)))
    return result

def route_human_gate_node(state: AgentState):
    return state["human_feedback"]["decision"]
