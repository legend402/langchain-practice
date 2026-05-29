from src.config import AgentState
from src.utils import node_hook
from src.utils.agent import get_state_message
from src.nodes._base import create_structure_node, next_redirect

knowledge_prompt = """
你是 knowledge_worker，负责生成结构化知识点总结。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

阅读笔记摘要：
{read_notes_summary}

分析结果：
{analysis_result}

标签：
{tags}

来源索引：
{source_index}

你的任务：

1. 生成清晰的知识标题。
2. 写出准确简洁的 summary。
3. 提炼关键知识点。
4. 按层级组织详细内容。
5. 给出必要例子。
6. 标注常见误解或注意事项。
7. 保留来源 id。
8. 使用已有 tags。
9. 给出 confidence。

要求：

- 不要编造事实。
- 不要引入与用户问题无关的内容。
- 不要把不确定内容写成确定事实。
- 不要生成思维导图相关内容
- finalize 会负责最终表达，你只负责结构化知识内容。

只输出 JSON：

{{
  "knowledge_summary": {{
    "title": "知识标题",
    "summary": "一句到三句话概括",
    "key_points": ["关键知识点"],
    "details": [
      {{
        "heading": "小节标题",
        "content": "小节内容"
      }}
    ],
    "examples": ["例子"],
    "common_misunderstandings": ["常见误解或注意事项"],
    "tags": {{
      "domain": [],
      "topic": [],
      "difficulty": "beginner | intermediate | advanced",
      "knowledge_type": [],
      "keywords": []
    }},
    "sources": ["src_001"],
    "confidence": 0.0
  }},
  "trace": ["knowledge_worker completed"]
}}
"""

def knowledge_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "read_notes_summary": state.get("read_notes_summary", ""),
        "analysis_result": state.get("analysis_result"),
        "tags": state.get("tags"),
        "source_index": state.get("source_index", []),
    }

@node_hook(after_hook=next_redirect)
def knowledge_node(state: AgentState):
    result = create_structure_node(state, knowledge_prompt, knowledge_input)
    result["messages"] = state["messages"] + [("AI", get_state_message("knowledge", result))]
    return result
