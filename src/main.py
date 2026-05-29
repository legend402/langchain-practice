import asyncio
import os

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config import AgentState
from src.graph import _build_graph
from src.utils.rich_print import enable_rich_print
from src.utils.agent import get_initial_state

load_dotenv()
enable_rich_print()

async def main():
    pool = AsyncConnectionPool(os.getenv("PGSQL_DB_URI"), min_size=1, max_size=3)
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    agent = _build_graph(checkpointer)

    initial_state = get_initial_state({
        "user_query": "帮我总结一下这篇文章讲了什么：https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/%E7%AC%AC%E5%8D%81%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE.md",
    })

    async for event in agent.astream(initial_state, stream_mode=["updates", "custom"]):
        print(event)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
