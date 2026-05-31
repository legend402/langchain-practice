from src.config import AgentState
from src.utils import node_hook
from src.utils.agent import get_state_message
from src.agent.research.nodes._base import create_structure_node, next_redirect

tag_prompt = """
你是 tag_worker，负责为知识点总结生成标签和分类信息。

用户问题：
{user_query}

任务目标：
{task_goal}

分析摘要：
{analysis_summary}

分析结果：
{analysis_result}

你的任务：

1. 判断知识所属领域。
2. 提取具体主题标签。
3. 判断知识难度。
4. 判断知识类型。
5. 生成检索关键词。
6. 避免标签过多、重复、空泛。

标签要求：

- domain：大的领域，例如 AI、Python、LangGraph。
- topic：具体主题，例如 supervisor pattern、routing、human-in-the-loop。
- difficulty：只能是 beginner、intermediate、advanced。
- knowledge_type：例如 concept、workflow、architecture、implementation、best_practice。
- keywords：适合检索的关键词。

只输出 JSON：

{{
  "tags": {{
    "domain": ["领域标签"],
    "topic": ["主题标签"],
    "difficulty": "beginner | intermediate | advanced",
    "knowledge_type": ["concept | workflow | architecture | implementation | best_practice"],
    "keywords": ["关键词"]
  }},
  "trace": ["tag_worker completed"]
}}
"""


def tag_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "analysis_summary": state.get("analysis_summary"),
        "analysis_result": state.get("analysis_result"),
    }


@node_hook(after_hook=next_redirect)
async def tag_node(state: AgentState):
    result = await create_structure_node(state, tag_prompt, tag_input)
    result["messages"] = state["messages"] + [("ai", get_state_message("tag", result))]
    return result
