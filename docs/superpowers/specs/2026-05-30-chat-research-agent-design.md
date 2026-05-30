# Chat + Research Agent 设计文档

## 概述

将现有 research agent 改造为 chat 优先的架构，主 agent 负责日常对话，需要深度研究时通过 tool calling 触发 research subgraph。模仿 Claude Code / OpenCode 的 subagent 模式。

## 架构

```
START → chat ──→ END
          │
          └──→ (tool: research)
               research_subgraph (无 human_gate)
               supervisor → search → read → analyze → tag → knowledge → review → finalize
               review 不过时内部 replan 循环
               返回 final_answer 或 error 给主 agent
```

## State 设计

### ChatState（主图）

```python
class ChatState(TypedDict, total=False):
    messages: list[BaseMessage]  # LangChain 标准消息格式，支持多轮
    user_query: str
    research_result: Optional[str]  # research 完成后的结果
    research_active: bool           # 标记是否在执行 research
```

### AgentState（子图，不变）

现有 `AgentState` 保持不变，作为 research subgraph 的 state。

## Chat 节点

### 模型

chat 使用独立的、较轻量的模型（可通过配置指定），research 子图使用现有模型。

### System Prompt 要点

```
你是一个知识助手。你可以：
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
```

### Research Tool 定义

```python
{
    "name": "research",
    "description": "深度研究工具。当用户需要总结知识、分析资料、搜索多个来源后生成结构化报告时调用。",
    "parameters": {
        "user_query": "用户的研究问题",
        "task_goal": "研究目标（可选）",
    }
}
```

## Research Tool 内部实现

```python
async def execute_research(user_query: str, task_goal: str = "", config: dict = None) -> str:
    """执行 research 子图，通过 stream_writer 转发事件到主图"""
    research_graph = get_research_graph()
    initial_state = get_initial_state({"user_query": user_query, "task_goal": task_goal})
    writer = get_stream_writer()

    final_state = {}
    try:
        async for mode, event in research_graph.astream(
            initial_state,
            config={"configurable": {"thread_id": config["thread_id"]}},
            stream_mode=["updates", "custom"]
        ):
            if mode == "custom":
                event["source"] = "research"
                writer(event)
            elif mode == "updates" and "__interrupt__" not in event:
                node = list(event.keys())[0] if event else None
                if node:
                    writer({"source": "research", "type": "node_update", "node": node, "state": event})
                    final_state.update(event[node])

        return final_state.get("final_answer", "研究未产生结果")
    except Exception as e:
        return f"研究过程中出错: {str(e)}"
```

### 关键点

- tool 内部用 `astream` 而非 `ainvoke`，获取中间事件
- 所有事件通过 `stream_writer` 转发，带 `source: "research"` 标记
- review 不过时子图内部 replan 循环（现有逻辑）
- 去掉 human_gate，子图完全自主完成
- 错误由主 agent 判断是否重试

## Research Subgraph

### 与现有 graph 的差异

- 移除 `human` 节点和 `human_gate` 相关逻辑
- 移除 `route_human_gate_node` 和 `route_human_gate_node` 的 conditional edges
- review 的 `need_human` 路径改为 `replan`
- 其余节点（supervisor、search、read、analyze、tag、knowledge、review、finalize）保持不变

### 子图结构

```
START → supervisor → search/read/analyze/tag/knowledge → supervisor
                   → review → (replan) → supervisor
                            → (pass) → finalize → END
```

## Event Generator 改造

现有 `event_generator` 需要根据事件来源区分处理：

```python
async for mode, state in main_graph.astream(..., stream_mode=["updates", "custom"]):
    if mode == "custom":
        source = state.get("source")
        if source == "research":
            # research 子图转发的事件
            if state.get("type") == "node_update":
                # research 节点完成 → 存 DB + 透传前端
            else:
                # research 流式文本 → 透传前端
        else:
            # chat 流式文本 → 存 DB + 透传前端

    if mode == "updates":
        # 只有 chat 节点完成才会到这
```

## DB 存储

复用现有 `ChatMessage` 表，通过 `node_name` 字段区分：
- chat 消息：`node_name = "chat"`
- research 中间步骤：`node_name = "search"/"read"/...` （现有逻辑）
- research 最终结果：`node_name = "finalize"`

## 前端适配

1. SSE 解析：根据 `source` 字段区分 chat 和 research 事件
2. chat 消息：正常气泡展示
3. research 执行中：展示现有的加载动画（per-node loading text）
4. chat 的 `stream_chunk`：逐字输出，和 research finalize 的逐字输出复用同一逻辑

## 文件变更清单

### 新增文件
- `src/nodes/chat.py` — chat 节点 + system prompt
- `src/graph_chat.py` — 主图构建（chat + research tool）
- `src/tools/research.py` — research tool 定义与实现

### 修改文件
- `src/config.py` — 新增 `ChatState`
- `src/graph.py` — 移除 human_gate，导出独立的 research subgraph 构建函数
- `src/nodes/__init__.py` — 移除 human_gate 导出
- `src/nodes/reviewer.py` — `need_human` 路径改为 `replan`
- `src/service/__init__.py` — 主图使用新的 `graph_chat` 构建
- `src/service/routes/sse.py` — event_generator 根据事件来源区分处理
- `src/service/routes/chat.py` — 适配新的主图接口
- `src/main.py` — 适配新图结构
- `frontend/src/hooks/useAgentChat.ts` — 根据 source 区分 chat/research 事件
- `frontend/src/components/MessageList.tsx` — 支持展示 chat 类型消息
