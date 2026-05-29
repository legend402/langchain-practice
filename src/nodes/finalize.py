from langchain_classic.prompts import ChatPromptTemplate
from langgraph.graph.ui import get_stream_writer

from src.config import AgentState
from src.llm import init_model
from src.utils import node_hook
from src.utils.agent import get_state_message

finalize_prompt = """
你是 finalize，负责生成最终面向用户的知识点总结。

用户问题：
{user_query}

任务目标：
{task_goal}

输出偏好：
{output_preferences}

知识点总结：
{knowledge_summary}

标签：
{tags}

来源索引：
{source_index}

审核结果：
{review_result}

人工反馈：
{human_feedback}

你的任务：

1. 基于 knowledge_summary 生成最终答案。
2. 使用清晰的 Markdown 结构。
3. 保留标题、摘要、核心知识点、详细说明、例子、注意事项。
4. 如有来源，放在最后。
5. 如有标签，简洁展示。
6. 不要暴露内部 state、route、worker 等实现细节。
7. 不要引入新的事实。
8. 不要重新分析或修改已通过审核的核心结论。

如果 review_result.status 不是 pass，且 human_feedback.decision 不是 approved，不要输出正式总结，应说明仍需确认。

只输出最后的markdown文本
"""

def finalize_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "output_preferences": state.get("output_preferences", {}),
        "knowledge_summary": state.get("knowledge_summary"),
        "tags": state.get("tags"),
        "source_index": state.get("source_index", []),
        "review_result": state.get("review_result"),
        "human_feedback": state.get("human_feedback"),
    }

@node_hook()
async def finalize_node(state: AgentState):
    # result = create_structure_node(state, finalize_prompt, finalize_input)
    llm = init_model()
    writer = get_stream_writer()
    messages = ChatPromptTemplate.from_messages([
        ("system", finalize_prompt)
    ]).format_messages(**finalize_input(state))

    full_text = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_text += chunk.content
            writer({"stream_chunk": {"chunk": chunk.content, "node_output_key": "finalize"}})

    final_state = {
        "final_answer": full_text,
        "trace": ["finalize completed"],
    }
    final_state["messages"] = state["messages"] + [("AI", get_state_message("finalize", final_state))]
    return final_state
