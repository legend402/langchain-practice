from langchain_classic.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.config import AgentState, SearchResult, SourceMaterial
from src.llm import init_model
from src.utils.agent import get_state_message

supervisor_prompt = """
你是知识点总结 Agent 的 supervisor。

你的职责是根据当前流程摘要决定下一步进入哪个节点。
你不能直接完成知识总结，也不能输出最终答案。

历史消息：
{messages}

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

输出偏好：
{output_preferences}

当前流程状态：
{workflow_flags}

用户资料摘要：
{source_materials_summary}

搜索结果摘要：
{search_results_summary}

阅读笔记摘要：
{read_notes_summary}

分析摘要：
{analysis_summary}

最近审核结果：
{review_result}

最近人工反馈：
{human_feedback}

迭代次数：
{iteration_count} / {max_iterations}

最近错误：
{recent_errors}

你只能从以下 next 中选择一个：

- search: 搜索补充资料
- read: 阅读已有资料并提取笔记
- analyze: 分析阅读笔记，构建知识结构
- tag: 为知识点生成标签和分类
- knowledge: 生成结构化知识点总结
- review: 审核知识点总结质量（finalize 前置必经步骤）
- human: 需要用户确认或补充信息
- finalize: 输出最终答案（必须 review 通过后才能进入）

决策规则：
0. 用户提问需要结合[最近人工反馈]联合分析
1. 如果用户问题不清楚，或缺少必要目标、范围、输出要求，并且[最近人工反馈]没有反馈有效内容，选择 human。
2. 如果已超过最大迭代次数，选择 human。
3. 如果没有用户资料、搜索结果、阅读笔记，并且从用户问题看需要外部资料，选择 search。
4. 如果用户问题本身已经足够简单，且不需要外部资料，可以直接选择 analyze。
5. 如果已有用户资料或搜索结果，但还没有阅读笔记，选择 read。
6. 如果已有阅读笔记，但阅读笔记摘要显示信息明显不足，选择 search 或 human。
7. 如果已有阅读笔记且信息基本足够，但没有分析结果，选择 analyze。
8. 如果已有分析结果，但分析摘要显示缺少关键资料，选择 search 或 read。
9. 如果已有分析结果，但没有 has_tags 为 False，选择 tag。
10. 如果已有分析结果和 has_tags 为 True， has_knowledge_summary 为 False，选择 knowledge。
11. 如果 has_knowledge_summary 为 True，但没有 review_result，选择 review (禁止跳过)。
12. 如果 review_result.status 是 pass，选择 finalize。
13. 如果 review_result.status 是 need_human，选择 human。
14. 如果 review_result.status 是 replan，优先根据 review_result.next_action_hint 选择下一步；如果没有 hint，根据 issues 判断 search、read、analyze、tag 或 knowledge。
15. 如果 human_feedback.decision 是 approved，选择 finalize。
16. 如果 human_feedback.decision 是 revise 或 extra_input，根据反馈内容选择 search、read、analyze、tag、knowledge 或 review。

重要约束：
- 你必须严格按照规则顺序检查
- 禁止跳过任何中间步骤
- review 是 finalize 的绝对前置步骤，任何情况下禁止绕过 review 直接进入 finalize
- review_result 为 None、null、空字符串、空字典 {{}} 或未定义时，一律视为"没有 review_result"
- finalize 只能在 review_result.status 为 pass 或 human_feedback.decision 为 approved 时选择
- 如果不确定，选择最保守的选项（即排在更前面的规则）

先思考，再选择 next。严格按照以下 JSON 格式输出，supervisor_reason 必须写在 next 前面：

{{
  "supervisor_reason": "先简短说明选择原因，引用具体规则编号",
  "next": "search | read | analyze | tag | knowledge | review | human | finalize"
}}

示例（严格按照规则判断）：

示例1：has_knowledge_summary=True, review_result=None
{{"supervisor_reason": "has_knowledge_summary 为 True，但 review_result 为 None，根据规则11应选择 review", "next": "review"}}

示例2：review_result.status=pass
{{"supervisor_reason": "review_result.status 为 pass，根据规则12选择 finalize", "next": "finalize"}}

示例3：has_analysis_result=True, has_tags=False
{{"supervisor_reason": "有分析结果但 has_tags 为 False，根据规则9选择 tag", "next": "tag"}}
"""

def supervisor_input(state: AgentState) -> dict:
    return {
        "messages": state.get("messages", []),
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "output_preferences": state.get("output_preferences", {}),
        "workflow_flags": {
            "has_source_materials": bool(state.get("source_materials")),
            "has_search_results": bool(state.get("search_results")),
            "has_read_notes": bool(state.get("read_notes")),
            "has_read_notes_summary": bool(state.get("read_notes_summary")),
            "has_analysis_result": bool(state.get("analysis_result")),
            "has_analysis_summary": bool(state.get("analysis_summary")),
            "has_tags": bool(state.get("tags")),
            "has_knowledge_summary": bool(state.get("knowledge_summary")),
        },
        "source_materials_summary": summarize_source_materials(
            state.get("source_materials", [])
        ),
        "search_results_summary": summarize_search_results(
            state.get("search_results", [])
        ),
        "read_notes_summary": state.get("read_notes_summary", ""),
        "analysis_summary": state.get("analysis_summary", ""),
        "review_result": state.get("review_result"),
        "human_feedback": state.get("human_feedback"),
        "iteration_count": state.get("iteration_count"),
        "max_iterations": state.get("max_iterations"),
        "recent_errors": state.get("errors", [])[-3:],
    }

def summarize_search_results(search_results: list[SearchResult], limit: int = 5) -> list[dict]:
    return [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "source_type": item.get("source_type"),
            "relevance": item.get("relevance"),
            "credibility": item.get("credibility"),
        }
        for item in search_results[:limit]
    ]

def summarize_source_materials(source_materials: list[SourceMaterial], limit: int = 5) -> list[dict]:
    return [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "source_type": item.get("source_type"),
            "content_preview": item.get("content", "")[:200],
        }
        for item in source_materials[:limit]
    ]

def _validate_supervisor_result(result: dict, state: AgentState) -> dict:
    next_val = result.get("next", "")
    reason = result.get("supervisor_reason", "")
    review_result = state.get("review_result")
    human_feedback = state.get("human_feedback")
    has_knowledge_summary = bool(state.get("knowledge_summary"))

    if next_val == "finalize":
        review_passed = (
            isinstance(review_result, dict)
            and review_result.get("status") == "pass"
        )
        human_approved = (
            isinstance(human_feedback, dict)
            and human_feedback.get("decision") == "approved"
        )
        if not review_passed and not human_approved:
            corrected = "review" if has_knowledge_summary else "knowledge"
            result["next"] = corrected
            result["supervisor_reason"] = (
                f"[自动修正] 原因: finalize 未通过校验（review_result={review_result}, "
                f"human_feedback={human_feedback}），已修正为 {corrected}。原始原因: {reason}"
            )
    return result

def supervisor_node(state: AgentState):
    llm = init_model()
    system_prompt = ChatPromptTemplate.from_messages([
        ("system", supervisor_prompt),
    ])
    supervisor_chain = system_prompt | llm | JsonOutputParser()
    result = supervisor_chain.invoke(supervisor_input(state))
    result = _validate_supervisor_result(result, state)
    messages = state["messages"] + [("AI", get_state_message("supervisor", result))]
    result["messages"] = messages
    return result

def route_supervisor_node(state: AgentState):
    """总体路由"""
    return state["next"]
