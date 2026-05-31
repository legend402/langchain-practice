from langchain_community.tools import tool
from langgraph.graph.ui import get_stream_writer

from src.agent.research.graph import create_research_agent
from src.utils.agent import get_initial_state


@tool
async def research(user_query: str, task_goal: str = "") -> str:
    """
    深度研究工具。当用户需要总结知识、分析资料、搜索多个来源后生成结构化报告时调用。
    适合需要搜索、阅读、分析多个来源后生成结构化总结的场景。
    当用户消息以 /research 开头时必须调用此工具。
    :user_query str: 用户提出的研究问题
    :task_goal str: 任务达成的目标
    """
    research_agent = create_research_agent()

    initial_state = get_initial_state(
        {"user_query": user_query, "task_goal": task_goal}
    )

    writer = get_stream_writer()
    final_state: dict = {}

    try:
        async for mode, state in research_agent.astream(
            initial_state, stream_mode=["updates", "custom"]
        ):
            if mode == "custom":
                state["source"] = "research"
                writer(state)
            elif mode == "updates":
                if not state:
                    continue
                node = list(state.keys())[0]
                if node == "__interrupt__":
                    continue
                writer(
                    {
                        "source": "research",
                        "type": "node_update",
                        "node": node,
                        "state": state,
                    }
                )
                if node in state and isinstance(state[node], dict):
                    final_state.update(state[node])

        return final_state.get("final_answer", "研究未产生结果")
    except Exception as e:
        return f"研究过程中出错: {str(e)}"
