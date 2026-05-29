from src.config import AgentState
from src.utils import node_hook
from src.utils.agent import get_state_message
from src.nodes._base import create_structure_node, next_redirect

reader_prompt = """
你是 reader_worker，负责阅读资料并提取结构化笔记。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

用户提供的原始资料：
{source_materials}

搜索结果：
{search_results}

你的任务：

1. 阅读用户资料和搜索结果摘要。
2. 提取核心观点。
3. 提取关键定义。
4. 提取重要例子。
5. 提取可以支撑后续总结的证据。
6. 标注不确定、冲突或需要进一步确认的内容。
7. 为后续分析生成简洁的 read_notes_summary。

不要写最终总结。
不要做大范围发挥。
不要把没有来源的信息写成事实。

只输出 JSON：

{{
  "read_notes": [
    {{
      "source_id": "src_001",
      "title": "资料标题",
      "key_points": ["关键点"],
      "definitions": ["定义"],
      "examples": ["例子"],
      "uncertainties": ["不确定点"]
    }}
  ],
  "read_notes_summary": "用简洁文字概括全部阅读笔记，控制在 300-600 字以内",
  "evidence_items": [
    {{
      "source_id": "src_001",
      "claim": "可以被后续总结使用的结论",
      "support": "支撑依据摘要",
      "confidence": 0.0
    }}
  ],
  "trace": ["reader_worker completed"]
}}
"""

def reader_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "source_materials": state.get("source_materials", []),
        "search_results": state.get("search_results", [])[:8],
    }

@node_hook(after_hook=next_redirect)
async def read_node(state: AgentState):
    result = await create_structure_node(state, reader_prompt, reader_input)
    result["messages"] = [("AI", get_state_message("read", result))]
    return result
