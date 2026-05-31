from src.config import AgentState
from src.utils import node_hook
from src.utils.agent import get_state_message
from src.agent.research.nodes._base import create_structure_node, next_redirect

analyze_prompt = """
你是 analyse_worker，负责把阅读笔记分析成清晰的知识结构。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

阅读笔记摘要：
{read_notes_summary}

证据条目：
{evidence_items}

你的任务：

1. 提炼核心概念。
2. 建立知识点层级结构。
3. 说明概念之间的关系。
4. 提炼重点、难点和易混淆点。
5. 识别缺失信息和开放问题。
6. 区分主干知识和补充知识。

不要写最终文章。
不要引入没有依据的新事实。
如果信息不足，要写入 missing_information。

只输出 JSON：

{{
  "analysis_result": {{
    "core_concepts": ["核心概念"],
    "structure": [
      {{
        "topic": "一级知识点",
        "children": ["二级知识点"]
      }}
    ],
    "relationships": [
      {{
        "from": "概念 A",
        "to": "概念 B",
        "relation": "depends_on | causes | contrasts_with | part_of | explains"
      }}
    ],
    "key_insights": ["关键洞察"],
    "difficult_points": ["难点"],
    "missing_information": ["缺失信息"],
    "open_questions": ["待确认问题"]
  }},
  "analysis_summary": "对分析结果的简短摘要，控制在 200-400 字以内",
  "trace": ["analyst_worker completed"]
}}
"""


def analyse_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "read_notes_summary": state.get("read_notes_summary", ""),
        "evidence_items": state.get("evidence_items", []),
    }


@node_hook(after_hook=next_redirect)
async def analyze_node(state: AgentState):
    result = await create_structure_node(state, analyze_prompt, analyse_input)
    result["messages"] = state["messages"] + [
        ("ai", get_state_message("analyze", result))
    ]
    return result
