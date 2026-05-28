import asyncio
from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os

from config import AgentState
from graph import _build_graph
from utils.rich_print import enable_rich_print

load_dotenv()

enable_rich_print()

async def main():
  initial_state: AgentState = {
    "user_query": "帮我总结一下这篇文章讲了什么：https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/%E7%AC%AC%E5%8D%81%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE.md",
    "task_goal": "根据用户问题或资料生成结构化知识点总结",
    "constraints": [],
    "output_preferences": {
        "format": "markdown",
        "language": "zh-CN",
    },

    "source_materials": [],
    "search_results": [],
    "source_index": [],

    "read_notes": [],
    "read_notes_summary": "",
    "evidence_items": [],

    "analysis_result": None,
    "analysis_summary": None,
    "tags": None,
    "knowledge_summary": None,

    "review_result": None,
    "human_feedback": None,

    "final_answer": None,

    "next": None,
    "supervisor_reason": None,
    "iteration_count": 0,
    "max_iterations": 8,
    "errors": [],
    "trace": [],
  }

  pool = AsyncConnectionPool(os.getenv("PGSQL_DB_URI"), min_size=1, max_size=3)
  await pool.open()
  checkpointer = AsyncPostgresSaver(pool)
  await checkpointer.setup()
  agent = _build_graph(checkpointer)

  async for event in agent.astream(initial_state, stream_mode=["updates", "custom"]):
    print(event)

  await pool.close()

if __name__ == "__main__":
  asyncio.run(main())
