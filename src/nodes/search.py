from langchain_classic.prompts import ChatPromptTemplate

from src.agent.create_tools_agent import create_tools_agent
from src.config import AgentState
from src.llm import init_model
from src.utils import extract_json, node_hook
from src.utils.agent import get_state_message
from src.nodes._base import next_redirect

search_prompt = """
你是 searcher_worker，负责为知识点总结任务寻找资料来源。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

已有来源索引：
{existing_source_index}

调度原因：
{supervisor_reason}

你的任务：

1. 判断需要补充哪些资料。
2. 设计搜索关键词。
3. 找出与用户问题最相关的资料来源。
4. 优先选择官方文档、论文、教材、标准文档、权威文章。
5. 排除不相关，重复、低质量、广告化、来源不明的内容。
6. 给每个搜索结果标注相关性和可信度。
7. 最后最多保存3篇相关内容

不要生成知识点总结。
不要做深入分析。
不要输出长篇解释。
完整的网页正文内容存入content字段，超过5000字就自动精简，但是要保证重要信息不丢失

不要输出任何多余的内容，只输出 JSON:
{{
  "search_results": [
    {{
      "id": "src_001",
      "title": "资料标题",
      "url": "资料链接或 null",
      "snippet": "资料摘要",
      "content": "网页正文全部内容",
      "source_type": "official_doc | paper | book | article | blog | unknown",
      "relevance": 0.0,
      "credibility": "high | medium | low"
    }}
  ],
  "source_index": [
    {{
      "id": "src_001",
      "title": "资料标题",
      "url": "资料链接或 null",
      "source_type": "official_doc | paper | book | article | blog | unknown",
      "credibility": "high | medium | low",
      "used_by": ["searcher_worker"]
    }}
  ],
  "trace": ["searcher_worker completed"]
}}
"""

def searcher_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "existing_source_index": state.get("source_index", []),
        "supervisor_reason": state.get("supervisor_reason"),
    }

@node_hook(after_hook=next_redirect)
def search_node(state: AgentState):
    from src.tools.web_search import web_search
    from src.tools.web_fetch import web_fetch

    llm = init_model()
    messages = ChatPromptTemplate.from_messages([
        ("system", search_prompt)
    ]).format_messages(**searcher_input(state))

    llm_with_tools = create_tools_agent(llm=llm, tools=[web_search, web_fetch])
    response = llm_with_tools.invoke(messages)

    search_state = extract_json(response[-1].content)
    if search_state is None:
        return {
            "errors": ["search流程获取数据异常"]
        }

    search_state["messages"] = state["messages"] + [("AI", get_state_message("search", search_state))]
    return search_state
