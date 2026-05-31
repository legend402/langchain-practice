import asyncio
import json
import os
from uuid import uuid4

from dotenv import load_dotenv

from src.agent.chat.config import get_initial_chat_state

load_dotenv()
from langchain.messages import AIMessageChunk
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.agent.chat.create_agent import create_chat_agent
from src.config import AgentState
from src.agent.research.graph import _build_graph
from src.utils.rich_print import enable_rich_print
from src.utils.agent import get_initial_state

enable_rich_print()


async def main():
    pool = AsyncConnectionPool(os.getenv("PGSQL_DB_URI"), min_size=1, max_size=3)
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    agent = create_chat_agent(checkpointer)

    # initial_state = get_initial_state(
    #     {
    #         "user_query": "帮我总结一下这篇文章讲了什么：https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter10/%E7%AC%AC%E5%8D%81%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E9%80%9A%E4%BF%A1%E5%8D%8F%E8%AE%AE.md",
    #     }
    # )
    thread_id = uuid4()
    initial_state = get_initial_chat_state(
        {"user_query": ""},  # ，请帮我研究一下半导体领域的CPO是的前景
    )
    while True:
        text = input("user:").strip()
        initial_state["user_query"] = text
        initial_state["messages"] = initial_state["messages"] + [("human", text)]

        async for mode, data in agent.astream(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=["updates", "custom", "messages"],
        ):
            if mode == "messages":
                token, metadata = data
                if isinstance(token, AIMessageChunk) and token.content:
                    node = metadata.get("langgraph_node", "chat")
                    print(token.content, end="", flush=True)
                continue

            if mode == "custom":
                source = data.get("source")
                if source == "research":
                    event_type = data.get("type")
                    if event_type == "node_update":
                        node = data.get("node")
                        node_state = data.get("state", {})
                        print(node_state)
                continue

            if mode == "updates":
                if not data:
                    continue
                node = list(data.keys())[0]
                # if "messages" in data.get(node, {}):
                #     del data[node]["messages"]

                print(data)
                initial_state["messages"] = (
                    initial_state["messages"] + data[node]["messages"]
                )

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
