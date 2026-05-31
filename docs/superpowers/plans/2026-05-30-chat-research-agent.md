# Chat + Research Agent 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 research agent 改造为 chat 优先架构，主 agent 处理日常对话，需要深度研究时通过 tool calling 触发 research subgraph。

**Architecture:** 主图只有一个 chat 节点，绑定 research tool。LLM 自主决定是否调用 research。Research 子图是现有 graph 移除 human_gate 后的版本，tool 内部通过 astream + stream_writer 转发事件到主图 SSE。

**Tech Stack:** LangGraph (StateGraph, CompiledStateGraph, stream_writer), LangChain (ChatOpenAI, tool calling), FastAPI SSE, React TypeScript

---

## 文件结构

### 新增文件
| 文件 | 职责 |
|------|------|
| `src/config_chat.py` | ChatState 定义 |
| `src/nodes/chat.py` | chat 节点 + system prompt + 流式输出 |
| `src/tools/research.py` | research tool 定义与实现（astream + stream_writer 转发） |
| `src/graph_chat.py` | 主图构建（chat 节点 + research tool 绑定） |

### 修改文件
| 文件 | 改动 |
|------|------|
| `src/graph.py` | 移除 human_gate 节点和边，导出 `_build_research_graph` |
| `src/nodes/__init__.py` | 移除 human_gate 导出 |
| `src/nodes/reviewer.py` | prompt 移除 need_human 选项，只保留 pass/replan |
| `src/nodes/supervisor.py` | prompt 移除 human 相关规则 |
| `src/service/__init__.py` | 使用新的主图 `graph_chat` |
| `src/service/routes/sse.py` | event_generator 区分 chat/research 事件 |
| `src/service/routes/chat.py` | 适配新主图，移除 feedback 相关路由 |
| `src/main.py` | 适配新图 |
| `frontend/src/types/agent.ts` | 新增 chat 相关 SSE event 类型 |
| `frontend/src/hooks/useAgentChat.ts` | 区分 chat/research 事件，支持 chat 消息流式展示 |
| `frontend/src/components/MessageList.tsx` | 支持展示 chat 类型消息 |

---

### Task 1: 新增 ChatState 定义

**Files:**
- Create: `src/config_chat.py`

- [ ] **Step 1: 创建 ChatState**

```python
# src/config_chat.py
from typing import TypedDict, Optional
from langchain_core.messages import BaseMessage


class ChatState(TypedDict, total=False):
    messages: list[BaseMessage]
    user_query: str
    research_result: Optional[str]
    research_active: bool
```

- [ ] **Step 2: Commit**

```bash
git add src/config_chat.py
git commit -m "feat: add ChatState definition for main graph"
```

---

### Task 2: 改造 research subgraph（移除 human_gate）

**Files:**
- Modify: `src/graph.py`
- Modify: `src/nodes/__init__.py`
- Modify: `src/nodes/reviewer.py`
- Modify: `src/nodes/supervisor.py`
- Modify: `src/config.py`

- [ ] **Step 1: 修改 `src/nodes/reviewer.py` — 移除 need_human**

将 `reviewer_prompt` 中的审核结果选项从三个改为两个，移除 `need_human` 相关内容：

将 prompt 中的：
```
审核结果只能是：

- pass：可以进入 finalize。
- replan：系统可以自行修复，应回到 supervisor。
- need_human：必须由用户确认，应进入 human_gate。
```

改为：
```
审核结果只能是：

- pass：可以进入 finalize。
- replan：系统可以自行修复，应回到 supervisor。
```

将 JSON 输出模板中的：
```
"status": "pass | replan | need_human",
```
改为：
```
"status": "pass | replan",
```

移除 `"need_human_reason"` 字段。

- [ ] **Step 2: 修改 `src/config.py` — ReviewStatus 和 NextStep 类型**

将 `ReviewStatus` 类型：
```python
ReviewStatus = Literal[
    "pass",
    "replan",
    "need_human",
]
```
改为：
```python
ReviewStatus = Literal[
    "pass",
    "replan",
]
```

将 `NextStep` 类型中移除 `"human"` 选项。

- [ ] **Step 3: 修改 `src/nodes/supervisor.py` — 移除 human 相关规则**

在 `supervisor_prompt` 中：
1. 移除 `最近人工反馈：` 占位符和 `{human_feedback}` 变量
2. 从 `next` 选项列表中移除 `human`
3. 移除所有引用 `human_feedback` 的规则
4. 最大迭代次数限制时改为选 `finalize` 并附带警告（而非 `human`）
5. 重新编号剩余规则

将 `supervisor_input` 函数中移除 `human_feedback` 字段。

将 `_validate_supervisor_result` 函数中移除 `human_approved` 相关逻辑。

- [ ] **Step 4: 修改 `src/nodes/__init__.py` — 移除 human_gate 导出**

```python
# src/nodes/__init__.py
from src.nodes.supervisor import supervisor_node, route_supervisor_node
from src.nodes.search import search_node
from src.nodes.reader import read_node
from src.nodes.analyzer import analyze_node
from src.nodes.tagger import tag_node
from src.nodes.knowledge import knowledge_node
from src.nodes.reviewer import reviewer_node, route_review_node
from src.nodes.finalize import finalize_node
```

- [ ] **Step 5: 修改 `src/graph.py` — 导出 research subgraph 构建函数**

```python
# src/graph.py
from langgraph.func import END, START
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config import AgentState
from src.nodes import (
    supervisor_node, search_node, read_node, analyze_node,
    tag_node, knowledge_node, reviewer_node,
    finalize_node, route_supervisor_node, route_review_node,
)


def _build_research_graph():
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("search", search_node)
    builder.add_node("read", read_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("tag", tag_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("review", reviewer_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("search", "supervisor")
    builder.add_edge("read", "supervisor")
    builder.add_edge("analyze", "supervisor")
    builder.add_edge("tag", "supervisor")
    builder.add_edge("knowledge", "supervisor")
    builder.add_edge("finalize", END)

    builder.add_conditional_edges("supervisor", route_supervisor_node, {
        "search": "search",
        "read": "read",
        "analyze": "analyze",
        "tag": "tag",
        "knowledge": "knowledge",
        "review": "review",
        "finalize": "finalize",
    })

    builder.add_conditional_edges("review", route_review_node, {
        "replan": "supervisor",
        "pass": "finalize",
    })

    return builder.compile()


def _build_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(AgentState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("search", search_node)
    builder.add_node("read", read_node)
    builder.add_node("analyze", analyze_node)
    builder.add_node("tag", tag_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("review", reviewer_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("search", "supervisor")
    builder.add_edge("read", "supervisor")
    builder.add_edge("analyze", "supervisor")
    builder.add_edge("tag", "supervisor")
    builder.add_edge("knowledge", "supervisor")
    builder.add_edge("finalize", END)

    builder.add_conditional_edges("supervisor", route_supervisor_node, {
        "search": "search",
        "read": "read",
        "analyze": "analyze",
        "tag": "tag",
        "knowledge": "knowledge",
        "review": "review",
        "finalize": "finalize",
    })

    builder.add_conditional_edges("review", route_review_node, {
        "replan": "supervisor",
        "pass": "finalize",
    })

    return builder.compile(checkpointer=checkpointer)
```

注意：`_build_research_graph()` 不传 checkpointer，作为 tool 内部使用的轻量子图。`_build_graph()` 保持原有签名，用于兼容旧的 CLI 调试入口。

- [ ] **Step 6: Commit**

```bash
git add src/graph.py src/nodes/__init__.py src/nodes/reviewer.py src/nodes/supervisor.py src/config.py
git commit -m "refactor: remove human_gate from research subgraph"
```

---

### Task 3: 新增 Research Tool

**Files:**
- Create: `src/tools/research.py`

- [ ] **Step 1: 创建 research tool**

```python
# src/tools/research.py
from langchain_core.tools import tool
from langgraph.graph.ui import get_stream_writer

from src.graph import _build_research_graph
from src.utils.agent import get_initial_state


@tool
async def research(user_query: str, task_goal: str = "") -> str:
    """深度研究工具。当用户需要总结知识、分析资料、搜索多个来源后生成结构化报告时调用。
    适合需要搜索、阅读、分析多个来源后生成结构化总结的场景。
    当用户消息以 /research 开头时必须调用此工具。"""
    research_graph = _build_research_graph()
    initial_state = get_initial_state({"user_query": user_query, "task_goal": task_goal})
    writer = get_stream_writer()

    final_state: dict = {}
    try:
        async for mode, event in research_graph.astream(
            initial_state,
            stream_mode=["updates", "custom"],
        ):
            if mode == "custom":
                event["source"] = "research"
                writer(event)
            elif mode == "updates":
                if not event:
                    continue
                node = list(event.keys())[0]
                if node == "__interrupt__":
                    continue
                writer({"source": "research", "type": "node_update", "node": node, "state": event})
                if node in event and isinstance(event[node], dict):
                    final_state.update(event[node])

        return final_state.get("final_answer", "研究未产生结果")
    except Exception as e:
        return f"研究过程中出错: {str(e)}"
```

- [ ] **Step 2: Commit**

```bash
git add src/tools/research.py
git commit -m "feat: add research tool with stream forwarding"
```

---

### Task 4: 新增 Chat 节点（标准 Agent 模式）

**Files:**
- Create: `src/nodes/chat.py`

核心设计：chat 节点只负责调用 LLM，不手动管理 tool calling 循环。主图通过 `chat → tools → chat` 循环自动处理 tool calls。流式输出由主图的 `stream_mode="messages"` 负责，chat 节点本身不需要 stream_writer。

- [ ] **Step 1: 创建 chat 节点**

```python
# src/nodes/chat.py
import os

from langchain_core.messages import SystemMessage

from src.config_chat import ChatState
from src.llm import init_model
from src.tools.research import research


CHAT_SYSTEM_PROMPT = """你是一个知识助手。你可以：
1. 直接回答用户的简单问题（闲聊、解释概念、提供建议）
2. 当用户需要深度研究时，调用 research 工具

触发 research 的场景：
- 用户要求总结、分析、深度研究某个话题
- 用户消息以 /research 开头（必须调用）
- 需要搜索多个来源并综合分析

不触发 research 的场景：
- 简单问答、闲聊、已有知识的解释

当 research 工具返回结果后：
- 如果结果质量 OK，基于结果生成最终回复
- 如果结果不完整或有误，可以再次调用 research 或补充说明

回复使用中文。"""


def init_chat_model():
    return init_model(
        base_url=os.getenv("CHAT_LLM_BASE_URL", None),
        model=os.getenv("CHAT_LLM_MODEL", None),
    )


async def chat_node(state: ChatState) -> dict:
    llm = init_chat_model()
    llm_with_tools = llm.bind_tools([research])

    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)] + state.get("messages", [])
    response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response]}
```

**说明：**
- chat_node 是纯粹的 LLM 调用，不手动管理 tool calling 循环
- 如果 LLM 返回 tool_calls，主图的 `tools` 节点会自动执行 tool，然后循环回 `chat`
- 如果 LLM 返回纯文本，主图直接结束
- 流式 token 输出由主图的 `stream_mode="messages"` 自动处理，chat_node 不需要 stream_writer

- [ ] **Step 2: Commit**

```bash
git add src/nodes/chat.py
git commit -m "feat: add chat node with standard agent pattern"
```

---

### Task 5: 新增主图构建（标准 Agent 循环）

**Files:**
- Create: `src/graph_chat.py`

- [ ] **Step 1: 创建主图**

主图采用标准 agent 模式：`chat` 节点调用 LLM，如果返回 tool_calls → `tools` 节点执行 → 循环回 `chat`。如果返回纯文本 → `END`。

```python
# src/graph_chat.py
from langgraph.func import END, START
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import ToolNode, tools_condition

from src.config_chat import ChatState
from src.nodes.chat import chat_node
from src.tools.research import research


def _build_chat_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(ChatState)

    builder.add_node("chat", chat_node)
    builder.add_node("tools", ToolNode([research]))

    builder.add_edge(START, "chat")
    builder.add_conditional_edges("chat", tools_condition, {
        "tools": "tools",
        END: END,
    })
    builder.add_edge("tools", "chat")

    return builder.compile(checkpointer=checkpointer)
```

**说明：**
- `ToolNode([research])`：LangGraph 内置的工具执行节点，自动处理 `ToolMessage` 的生成
- `tools_condition`：LangGraph 内置的条件路由，检查 `AIMessage` 是否包含 `tool_calls`，有则路由到 `"tools"`，无则路由到 `END`
- 循环：`chat → (有 tool_calls?) → tools → chat → ... → (无 tool_calls) → END`
- `stream_mode="messages"` 会自动流式输出每一轮 LLM 调用的 token，包括多轮 tool calling

- [ ] **Step 2: Commit**

```bash
git add src/graph_chat.py
git commit -m "feat: add main chat graph with standard agent loop"
```

---

### Task 6: 改造 Service 层

**Files:**
- Modify: `src/service/__init__.py`
- Modify: `src/service/routes/sse.py`
- Modify: `src/service/routes/chat.py`
- Modify: `src/utils/agent.py`

- [ ] **Step 1: 修改 `src/service/__init__.py` — 使用新的主图**

将 `from src.graph import _build_graph` 改为 `from src.graph_chat import _build_chat_graph`。

将 `app.state.agent = _build_graph(checkpointer)` 改为 `app.state.agent = _build_chat_graph(checkpointer)`。

- [ ] **Step 2: 修改 `src/service/routes/sse.py` — 区分 chat/research 事件，处理 messages 流式 token**

主要改动：
1. `stream_mode` 从 `["updates", "custom"]` 改为 `["updates", "custom", "messages"]`
2. 新增 `messages` 模式处理：提取 LLM token chunk，逐字推送给前端
3. `updates` 模式只处理 chat 节点完成事件（存 DB）
4. `custom` 模式处理 research 子图转发的中间事件

```python
# src/service/routes/sse.py
import asyncio
import json
from typing import Any
from asyncio import Task

from langchain_core.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config_chat import ChatState

type AgentType = CompiledStateGraph[ChatState, None, ChatState, ChatState]

async def event_generator(
    agent: AgentType,
    initial_state: Any,
    session_id: str,
    engine: AsyncEngine,
    sessions: dict,
    create_message_fn,
):
    task = asyncio.current_task()
    sessions[session_id] = task
    config = {"configurable": {"thread_id": session_id}}
    try:
        async for mode, data in agent.astream(
            initial_state, config,
            stream_mode=["updates", "custom", "messages"],
        ):
            if mode == "messages":
                token, metadata = data
                if isinstance(token, AIMessageChunk) and token.content:
                    node = metadata.get("langgraph_node", "chat")
                    event = {"stream_chunk": {"chunk": token.content, "node_output_key": node}}
                    yield f"data: {json.dumps(event)}\n\n"
                continue

            if mode == "custom":
                source = data.get("source")
                if source == "research":
                    event_type = data.get("type")
                    if event_type == "node_update":
                        node = data.get("node")
                        node_state = data.get("state", {})
                        async with AsyncSession(engine) as db:
                            await create_message_fn(
                                session=db,
                                thread_id=session_id,
                                role="AI",
                                node_name=node,
                                content="",
                                state=node_state,
                            )
                            await db.commit()
                    data["session_id"] = session_id
                    yield f"data: {json.dumps(data)}\n\n"
                continue

            if mode == "updates":
                if not data:
                    continue
                node = list(data.keys())[0]
                if "messages" in data.get(node, {}):
                    del data[node]["messages"]
                data["session_id"] = session_id
                async with AsyncSession(engine) as db:
                    await create_message_fn(
                        session=db,
                        thread_id=session_id,
                        role="AI",
                        node_name=node,
                        content="",
                        state=data,
                    )
                    await db.commit()
                yield f"data: {json.dumps(data)}\n\n"

    except asyncio.CancelledError:
        yield f"data: {json.dumps({'type': 'stopped', 'session_id': session_id})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'session_id': session_id, 'error': str(e)})}\n\n"
    finally:
        sessions.pop(session_id, None)
```

**说明：**
- `messages` 模式：LangGraph 自动流式输出每一轮 LLM 调用的 token。`AIMessageChunk.content` 是增量文本 chunk，`metadata["langgraph_node"]` 标识来自哪个节点。无论 LLM 是在输出 tool_calls 的参数还是纯文本，都会产生 stream event。前端只需要关心 `token.content` 非空的情况。
- `custom` 模式：只处理 research 子图通过 `stream_writer` 转发的中间事件（`source: "research"`）。
- `updates` 模式：只处理节点完成后的状态更新（存 DB）。

- [ ] **Step 3: 修改 `src/utils/agent.py` — 新增 recover_chat_state**

```python
def recover_chat_state(messages: list) -> "ChatState":
    from langchain_core.messages import HumanMessage, AIMessage
    from src.config_chat import ChatState
    state: ChatState = {"messages": []}
    for message in messages:
        if message.role == "human":
            state["messages"].append(HumanMessage(content=message.content))
        else:
            state["messages"].append(AIMessage(content=message.content or ""))
    return state
```

- [ ] **Step 4: 修改 `src/service/routes/chat.py` — 适配新主图**

主要改动：
1. `ChatStart` 新增 `task_goal` 可选字段
2. `chat_start` 使用 `ChatState` 的初始 state 而非 `AgentState`
3. 移除 `chat_feedback` 路由（不再需要 human gate）
4. 保留 `chat_stop` 路由

`state` 构建改为：
```python
from src.config_chat import ChatState
from langchain_core.messages import HumanMessage

# 新会话
chat_state: ChatState = {
    "messages": [HumanMessage(content=body.query)],
    "user_query": body.query,
}

# 已有会话（恢复历史）
chat_state = recover_chat_state(messages_from_db)
chat_state["messages"] = chat_state["messages"] + [HumanMessage(content=body.query)]
```

移除 `chat_feedback` 路由和 `ChatFeedback` model。

- [ ] **Step 5: Commit**

```bash
git add src/service/__init__.py src/service/routes/sse.py src/service/routes/chat.py src/utils/agent.py
git commit -m "feat: adapt service layer for chat graph"
```

---

### Task 7: 改造 main.py CLI 入口

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: 适配新图结构**

```python
# src/main.py
import asyncio
import os

from dotenv import load_dotenv
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage

from src.config_chat import ChatState
from src.graph_chat import _build_chat_graph
from src.utils.rich_print import enable_rich_print

load_dotenv()
enable_rich_print()

async def main():
    pool = AsyncConnectionPool(os.getenv("PGSQL_DB_URI"), min_size=1, max_size=3)
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    agent = _build_chat_graph(checkpointer)

    initial_state: ChatState = {
        "messages": [HumanMessage(content="帮我总结一下 LangGraph 的核心概念")],
        "user_query": "帮我总结一下 LangGraph 的核心概念",
    }

    async for event in agent.astream(initial_state, stream_mode=["updates", "custom", "messages"]):
        print(event)

    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: adapt CLI entry for chat graph"
```

---

### Task 8: 前端类型适配

**Files:**
- Modify: `frontend/src/types/agent.ts`

- [ ] **Step 1: 更新 SSEEventData 类型**

在 `SSEEventData` 中新增 chat 相关字段：

```typescript
export type SSEEventData = {
  stream_chunk: { chunk: string; node_output_key: NodeKey | "chat" };
  source?: "research" | "chat";
  type?: "node_update" | "research_start" | "research_end";
  node?: string;
  state?: Record<string, unknown>;
  result?: string;
  supervisor?: { supervisor_reason: string; next: string };
  search?: {
    search_results: SearchResult[];
    source_index: SourceIndexItem[];
    trace: string[];
  };
  read?: {
    read_notes: ReadNote[];
    read_notes_summary: string;
    evidence_items: EvidenceItem[];
    trace: string[];
  };
  analyze?: {
    analysis_result: AnalysisResult;
    analysis_summary: string;
    trace: string[];
  };
  tag?: { tags: Tags; trace: string[]; next: string };
  knowledge?: { knowledge_summary: KnowledgeSummary; trace: string[] };
  review?: { review_result: ReviewResult; trace: string[] };
  finalize?: { final_answer: string; trace: string[] };
  session_id?: string;
};
```

关键改动：`node_output_key` 类型扩展为 `NodeKey | "chat"`，新增 `source`、`type`、`node`、`result`、`state` 可选字段。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/agent.ts
git commit -m "feat: update SSE event types for chat mode"
```

---

### Task 9: 前端 useAgentChat 适配

**Files:**
- Modify: `frontend/src/hooks/useAgentChat.ts`

- [ ] **Step 1: 改造 handleMessage**

`handleMessage` 回调需要区分 chat 和 research 事件：

1. `stream_chunk` 事件：`node_output_key` 现在来自 `messages` stream mode 的 metadata，可以是 `"chat"`、`"tools"` 或 research 节点名。`"chat"` 节点的 token 作为 AI 对话消息逐字展示
2. `source === "research"` 且 `type === "node_update"` 的事件：走现有 research 节点更新逻辑
3. 移除 `human` 节点的处理逻辑
4. 移除 `showFeedbackPanel` 相关逻辑和 `submitFeedback` 方法

`stream_chunk` 分支核心逻辑（不需要大改，`node_output_key` 已包含节点名）：

```typescript
if (event.stream_chunk) {
  const { chunk, node_output_key } = event.stream_chunk;
  
  // tools 节点的 stream 不需要展示（是 tool call 参数的 JSON）
  if (node_output_key === "tools") return;
  
  setActiveNode(node_output_key);
  setMessages((prev) => {
    const lastMsg = prev[prev.length - 1];
    if (lastMsg && lastMsg.nodeName === node_output_key) {
      const updatedMsg = { ...lastMsg, content: lastMsg.content + chunk };
      return [...prev.slice(0, -1), updatedMsg];
    } else {
      return [...prev, {
        id: uuid(),
        role: "AI",
        content: chunk,
        timestamp: Date.now(),
        nodeName: node_output_key,
      }];
    }
  });
  return;
}
```

关键改动：
- 过滤掉 `node_output_key === "tools"` 的 stream_chunk（这是 tool call 参数的 JSON 片段，不应展示给用户）
- `node_output_key === "chat"` 的 token 会被创建为 `nodeName: "chat"` 的消息，前端用 MarkdownRenderer 渲染
- research 节点的 token 仍然复用现有逻辑

- [ ] **Step 2: 移除 FeedbackPanel 相关代码**

在 return 对象中移除 `showFeedbackPanel` 和 `submitFeedback`。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useAgentChat.ts
git commit -m "feat: adapt useAgentChat for chat/research event routing"
```

---

### Task 10: 前端 MessageList 适配

**Files:**
- Modify: `frontend/src/components/MessageList.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: MessageList — 支持 chat 消息展示**

在 `NODE_LOADING_TEXT` 中新增 `chat` 项：
```typescript
const NODE_LOADING_TEXT: Record<string, string> = {
  chat: "正在思考",
  supervisor: "正在规划研究路径",
  // ... 现有项保持不变
};
```

在 `NODE_ICON` 中新增 `chat` 项：
```typescript
const NODE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  chat: Sparkles,
  // ... 现有项保持不变
};
```

StepCard 中的 `nodeLabel` 映射新增：
```typescript
chat: "对话",
```

`nodeName === "chat"` 的消息应该直接用 `MarkdownRenderer` 渲染（而非 StepCard 或 ResultCard）。现有的消息渲染逻辑中，如果 `msg.nodeName === "chat"` 且没有 `msg.state`，会走到最后的 `else` 分支（`glass-card` + `MarkdownRenderer`），这已经是正确的展示方式，不需要额外改动。

- [ ] **Step 2: App.tsx — 移除 FeedbackPanel**

移除 `FeedbackPanel` 的导入和渲染。移除 `chat.showFeedbackPanel` 条件渲染。

```tsx
// App.tsx
import { useAgentChat } from "./hooks/useAgentChat";
import SearchForm from "./components/SearchForm";
import MessageList from "./components/MessageList";
import SessionSidebar from "./components/SessionSidebar";

export default function App() {
  const chat = useAgentChat();

  return (
    <div className="h-screen bg-background flex">
      <SessionSidebar
        sessions={chat.sessions}
        activeThreadId={chat.activeThreadId}
        onSelect={chat.loadSession}
        onNew={chat.startNewSession}
        onDelete={chat.deleteSession}
        collapsed={chat.sidebarCollapsed}
        onToggle={chat.toggleSidebar}
      />

      <div className={`flex-1 flex flex-col min-w-0 h-screen main-area ${chat.sidebarCollapsed ? "sidebar-collapsed" : "sidebar-expanded"}`}>
        <main className="flex-1 flex flex-col max-w-3xl w-full mx-auto px-4 overflow-hidden" style={{ height: "calc(100vh)" }}>
          <MessageList messages={chat.messages} loading={chat.loading} currentState={chat.currentState} activeNode={chat.activeNode} />
          <div className="shrink-0 pb-4 pt-0 space-y-3">
            <SearchForm onSubmit={chat.submit} onStop={chat.stop} loading={chat.loading} />
          </div>
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/MessageList.tsx frontend/src/App.tsx
git commit -m "feat: adapt frontend for chat message display"
```

---

### Task 11: 集成测试

**Files:**
- 无新增文件

- [ ] **Step 1: 启动后端服务，验证基本 chat 功能**

Run: `cd /Users/hanyangjing/Desktop/self-space/research && python -m uvicorn src.service:app --port 4030 --reload`

手动测试：
1. 发送简单问题（如"你好"），验证直接回复，不触发 research
2. 发送 `/research LangGraph 是什么`，验证触发 research 并展示中间过程
3. 发送自然语言研究请求（如"帮我总结一下 React hooks"），验证 LLM 自主触发 research
4. 多轮对话：先闲聊，再触发 research，再闲聊

- [ ] **Step 2: 启动前端，验证 SSE 流式展示**

Run: `cd /Users/hanyangjing/Desktop/self-space/research/frontend && npm run dev`

验证：
1. chat 消息逐字输出
2. research 中间步骤加载动画正常展示
3. research finalize 结果正常展示
4. 会话列表正常更新
5. 历史消息恢复正常

- [ ] **Step 3: Commit 集成修复（如有）**

```bash
git add -A
git commit -m "fix: integration fixes for chat + research agent"
```
