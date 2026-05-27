# Finalize 节点流式输出改造方案

## 1. 现状分析

当前 `finalize_node` 使用 `JsonOutputParser` 一次性解析出完整 JSON（包含 `final_answer` 字段），后端 `event_generator` 等整个节点执行完毕后才通过 SSE 发送一次完整结果。前端收到后一次性渲染。

**数据流：**

```
finalize_node → chain.invoke() → 完整 JSON → event_generator → SSE 一次性推送 → 前端一次性渲染
```

## 2. 改造目标

将 finalize 节点的输出改为流式，LLM 逐 token 生成，后端逐 chunk 通过 SSE 推送，前端逐字渲染 Markdown。

**目标数据流：**

```
finalize_node 内部:
  llm.astream() → 逐 chunk → get_stream_writer() 推送 → LangGraph 自动透传
                                                         ↓
event_generator 收到 mode="custom" 事件 → 通用转发给前端
```

## 3. 架构原则

- **节点级流式**：流式逻辑留在节点内部，`event_generator` 不关心具体节点
- **通用转发**：`event_generator` 只负责转发 `custom` 事件，未来新增流式节点无需改动
- **符合 LangGraph 设计**：利用 `get_stream_writer()` API，不 hack 框架

## 4. 具体改动

### 4.1 新建流式工具函数

**文件：`utils/streaming.py`**

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from llm import init_deepseek_model

async def stream_llm_output(system_prompt: str, user_input: dict, output_key: str):
    """
    通用的流式 LLM 输出工具函数
    节点内调用此函数即可实现流式推送，event_generator 无需关心具体节点

    Args:
        system_prompt: 系统提示词
        user_input: 用户输入数据
        output_key: 输出字段名（如 "final_answer"）

    Returns:
        str: 完整的生成文本
    """
    llm = init_deepseek_model()
    writer = get_stream_writer()

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=str(user_input))]

    full_text = ""
    async for chunk in llm.astream(messages):
        content = chunk.content
        if content:
            full_text += content
            writer({"chunk": content, "node_output_key": output_key})

    return full_text
```

### 4.2 改造 finalize_node

**文件：`nodes.py`**

```python
from utils.streaming import stream_llm_output

@node_hook()
async def finalize_node(state: AgentState):
    full_answer = await stream_llm_output(
        finalize_prompt,
        finalize_input(state),
        "final_answer",
    )
    return {
        "final_answer": full_answer,
        "messages": state["messages"] + [("AI", f"[finalize]: {full_answer}")],
    }
```

**关键变化：**

- 不再使用 `create_structure_node`（内部是 `chain.invoke()` + `JsonOutputParser`）
- 直接流式输出纯 Markdown，不再用 JSON 包装
- `finalize_prompt` 需要调整：不再要求输出 `{"final_answer": "...", "trace": [...]}` 格式，改为直接输出 Markdown 文本

### 4.3 改造 event_generator

**文件：`service/__init__.py`**

```python
async def event_generator(agent: AgentType, initial_state: Any, session: AsyncSession, session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    async for mode, state in agent.astream(initial_state, config, stream_mode=["updates", "custom"]):
        if mode == "custom":
            # 通用的流式 chunk 转发，不关心具体节点
            state["session_id"] = session_id
            yield f"data: {json.dumps({'stream_chunk': state})}\n\n"
            continue

        # 以下是原有的 updates 逻辑，完全不变
        if "__interrupt__" in state:
            interrupt_state = {"human": state["__interrupt__"][0].value, "session_id": session_id}
            yield f"data: {json.dumps(interrupt_state)}\n\n"
            continue

        node = list(state.keys())[0] if state else None
        state["session_id"] = session_id
        if "messages" in state:
            del state["messages"]
        await create_message(session=session, thread_id=session_id, role="AI", node_name=node, content="", state=state)
        yield f"data: {json.dumps(state)}\n\n"
```

**关键变化：**

- `async for _, state` 改为 `async for mode, state`，区分 `updates` 和 `custom` 两种事件
- `custom` 事件通用转发，无需知道具体节点

### 4.4 前端 - 扩展 SSE 事件类型

**文件：`frontend/src/types/agent.ts`**

```ts
export type SSEEventData = {
  // ... 现有类型不变 ...
  stream_chunk?: { chunk: string; node_output_key: string; session_id?: string };
};
```

### 4.5 前端 - useAgentChat.ts 处理流式 chunk

**文件：`frontend/src/hooks/useAgentChat.ts`**

在 `submit` 和 `submitFeedback` 的 `onMessage` 回调中增加流式处理：

```ts
onMessage: (event: SSEEventData) => {
  // 通用流式 chunk 处理
  if (event.stream_chunk) {
    const { chunk, node_output_key } = event.stream_chunk;
    const nodeKey = node_output_key as NodeKey;

    setMessages(prev => {
      const last = prev[prev.length - 1];
      if (last.nodeName === nodeKey) {
        return [...prev.slice(0, -1), {
          ...last,
          content: last.content + chunk,
        }];
      }
      return [...prev, {
        id: `stream-${nodeKey}`,
        role: "AI" as const,
        content: chunk,
        nodeName: nodeKey,
        timestamp: Date.now(),
      }];
    });

    if (event.session_id) {
      setActiveThreadId(event.session_id);
      refreshSessions();
    }
    return;
  }

  // 原有节点完成逻辑
  const nodeKey = getNodeKey(event);
  if (!nodeKey) return;
  // ... 后续逻辑不变 ...
}
```

**注意**：当节点完成时（`updates` 事件中的 finalize），需要判断是否已存在流式消息，如果存在则更新而非新增。

### 4.6 前端 - ResultCard 渲染

`ResultCard` 组件已使用 `MarkdownRenderer`，流式追加 `content` 时会自动 re-render。需确保：

- 流式期间 `state` 可能为空，此时直接用 `content` 渲染 Markdown
- `MarkdownRenderer` 对频繁更新场景不会闪烁（可考虑加 `memo` 优化）

## 5. finalize_prompt 调整

**现状**：要求 LLM 输出 JSON：
```json
{
  "final_answer": "Markdown 文本",
  "trace": ["finalize completed"]
}
```

**改造后**：要求 LLM 直接输出纯 Markdown，不包装 JSON：

```python
finalize_prompt = """
你是 finalize，负责生成最终面向用户的知识点总结。

请直接输出 Markdown 格式的知识点总结，不要输出 JSON，不要添加代码块包装。

## 输出要求
- 使用清晰的 Markdown 结构（标题、列表、粗体等）
- 语言简洁、结构化
- 包含关键知识点、定义、示例

## 可用信息
{context}
"""
```

## 6. 数据库存储

- 流式期间的中间 chunk **不存 DB**
- 只在节点完成（`updates` 事件）时，一次性将完整 `final_answer` 写入数据库
- 现有 `create_message` 逻辑不变

## 7. 前置条件检查

- **LangGraph 版本**：需 `>= 0.2.x`，确认 `get_stream_writer()` 可用
- **LLM 配置**：`init_deepseek_model()` 已设置 `streaming=True`，无需修改
- **graph.py**：无需修改，节点注册和路由不变

## 8. 方案优势

| 对比项 | 放 event_generator | 节点级流式（本方案） |
|--------|-------------------|-------------------|
| 新增流式节点 | 改 event_generator | 只改节点本身 |
| 耦合度 | 高，if/else 蔓延 | 低，通用转发 |
| 可维护性 | 差 | 好 |
| 符合 LangGraph 设计 | 否 | 是 |

## 9. 未来扩展

任何节点想支持流式输出，只需两步：

1. 在节点内调用 `stream_llm_output()` 或直接使用 `get_stream_writer()`
2. 前端 `onMessage` 中已有通用的 `stream_chunk` 处理逻辑，自动生效
