# Agent 系统

## 架构概览

两级 Agent 架构：
1. **Chat Agent**（`src/agent/chat/`）— 简单 ReAct，可直接回答或调用 research 工具
2. **Research Agent**（`src/agent/research/`）— 多步状态机，supervisor 协调多个 worker 节点

research 工具（`src/tools/research.py`）作为桥梁：Chat LLM 调用 `@tool research()`，内部创建并运行完整的 research 图。

## Chat Agent

文件：`src/agent/chat/`

### 状态（`config.py`）

```python
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str
    research_result: Optional[str]
    research_active: bool
```

### 图拓扑（`create_agent.py`）

```
START → chat → [有工具调用] → tools → chat → END
              → [无工具调用] → END
```

- `chat` 节点：LLM + 绑定 `[research]` 工具
- `tools` 节点：LangGraph `ToolNode`
- 工具调用条件：`tools_condition`（有 tool_calls → tools，否则 → END）

### 聊天节点（`nodes/chat.py`）

- 系统提示词决定是否触发 research：摘要、分析、深度研究、`/research` 前缀、多源综合
- 不触发：简单问答、聊天、基于已有知识的解释

## Research Agent

文件：`src/agent/research/`

### 状态（`src/config.py`）

`AgentState` TypedDict 包含 20+ 字段：messages, user_query, task_goal, constraints, output_preferences, source_materials, search_results, source_index, read_notes, evidence_items, analysis_result, tags, knowledge_summary, review_result, human_feedback, final_answer, next, supervisor_reason, iteration_count, max_iterations, errors, trace

### 图拓扑（`graph.py`）

```
START → supervisor
  supervisor →[route_supervisor_node]→ search | read | analyze | tag | knowledge | review | human | finalize

  search → supervisor    read → supervisor    analyze → supervisor
  tag → supervisor       knowledge → supervisor

  review →[route_review_node]→ replan→supervisor | pass→finalize | need_human→human
  human →[route_human_gate_node]→ approved→finalize | revise→supervisor | extra_input→supervisor

  finalize → END
```

### 路由函数

- `route_supervisor_node(state)` → `state["next"]`
- `route_review_node(state)` → `state["review_result"]["status"]`（pass/replan/need_human）
- `route_human_gate_node(state)` → `state["human_feedback"]["decision"]`（approved/revise/extra_input）

### 节点说明

| 节点 | 文件 | 功能 |
|------|------|------|
| supervisor | `supervisor.py` | 16 规则决策系统，决定下一步节点。验证不允许跳过 review 直接 finalize |
| search | `search.py` | 使用 `ToolsAgent` 调用 `web_search` + `web_fetch` 搜索外部资源 |
| read | `reader.py` | 阅读材料，提取结构化笔记 |
| analyze | `analyzer.py` | 分析笔记为知识层级结构 |
| tag | `tagger.py` | 生成分类标签（领域/主题/难度/类型） |
| knowledge | `knowledge.py` | 生成结构化知识总结 |
| review | `reviewer.py` | 审核知识总结的质量和完整性 |
| human_gate | `human_gate.py` | 人工介入节点，使用 `interrupt()` 暂停等待用户反馈 |
| finalize | `finalize.py` | 生成最终 Markdown 格式答案（流式输出，非 JSON 解析） |

### 通用节点模式（`_base.py`）

`create_structure_node(state, prompt, struct_input)`：
- 构建 `ChatPromptTemplate → LLM → JsonOutputParser` 链
- 出错时返回错误状态 + `next="supervisor"`

### 装饰器（`src/utils/__init__.py`）

`node_hook(after_hook=next_redirect)` — 所有 worker 节点用它确保返回 supervisor。

## ToolsAgent（`src/agent/create_tools_agent.py`）

通用 LLM 工具调用循环（非 LangGraph ToolNode）：
- 手动管理多轮工具调用（最多 10 轮）
- search 节点使用它来调用 web_search + web_fetch

## 工具（`src/tools/`）

| 工具 | 说明 |
|------|------|
| `research` | 桥接 chat → research agent 的 LangChain @tool |
| `web_search` | Tavily 搜索（query, max_results=5） |
| `web_fetch` | Tavily 批量 URL 内容提取（urls: list[str]） |

## LLM 配置（`src/llm.py`）

`init_model()` 创建 `ChatOpenAI` 实例：
- 默认：DeepSeek API（`deepseek-v4-flash`）
- 环境变量覆盖：`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`/`DEEPSEEK_API_KEY`
- 默认流式开启，max_tokens=100000
