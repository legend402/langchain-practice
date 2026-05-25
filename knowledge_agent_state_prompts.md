# LangGraph 知识点总结 Agent：State 与 Prompt 设计

本文档描述一套用于“知识点总结”的 LangGraph Agent 流程设计，包括完整 `State` 结构、节点输入切片方案，以及除 route 节点外各业务节点的 Prompt。

核心原则：

- `State` 可以保存完整上下文。
- Prompt 不直接塞完整 `state`。
- 每个节点只接收自己需要的 state slice。
- 大字段通过 summary、index、evidence_items 等压缩字段传递。
- route 节点不调用 LLM，只根据状态字段做条件跳转。

---

## 1. State 设计

```python
from typing import TypedDict, Literal, Optional, Any


NextStep = Literal[
    "search",
    "read",
    "analyze",
    "tag",
    "knowledge",
    "review",
    "human",
    "finalize",
]

ReviewStatus = Literal[
    "pass",
    "replan",
    "need_human",
]

HumanDecision = Literal[
    "approved",
    "revise",
    "extra_input",
]


class SourceMaterial(TypedDict, total=False):
    id: str
    title: str
    content: str
    source_type: str
    url: Optional[str]


class SearchResult(TypedDict, total=False):
    id: str
    title: str
    url: Optional[str]
    snippet: str
    content: str
    source_type: str
    relevance: float
    credibility: str


class SourceIndexItem(TypedDict, total=False):
    id: str
    title: str
    url: Optional[str]
    source_type: str
    credibility: str
    used_by: list[str]


class ReadNote(TypedDict, total=False):
    source_id: str
    title: str
    key_points: list[str]
    definitions: list[str]
    examples: list[str]
    uncertainties: list[str]


class EvidenceItem(TypedDict, total=False):
    source_id: str
    claim: str
    support: str
    confidence: float


class AnalysisResult(TypedDict, total=False):
    core_concepts: list[str]
    structure: list[dict[str, Any]]
    relationships: list[dict[str, str]]
    key_insights: list[str]
    difficult_points: list[str]
    missing_information: list[str]
    open_questions: list[str]


class Tags(TypedDict, total=False):
    domain: list[str]
    topic: list[str]
    difficulty: Literal["beginner", "intermediate", "advanced"]
    knowledge_type: list[str]
    keywords: list[str]


class KnowledgeSummary(TypedDict, total=False):
    title: str
    summary: str
    key_points: list[str]
    details: list[dict[str, str]]
    examples: list[str]
    common_misunderstandings: list[str]
    tags: Tags
    sources: list[str]
    confidence: float


class ReviewResult(TypedDict, total=False):
    status: ReviewStatus
    issues: list[str]
    suggestions: list[str]
    next_action_hint: Optional[NextStep]
    need_human_reason: Optional[str]
    confidence: float


class HumanFeedback(TypedDict, total=False):
    decision: HumanDecision
    comment: str
    additional_material: Optional[str]


class AgentState(TypedDict, total=False):
    # 用户输入
    user_query: str
    task_goal: str
    constraints: list[str]
    output_preferences: dict[str, Any]

    # 原始资料与搜索结果
    source_materials: list[SourceMaterial]
    search_results: list[SearchResult]
    source_index: list[SourceIndexItem]

    # 阅读与证据
    read_notes: list[ReadNote]
    read_notes_summary: str
    evidence_items: list[EvidenceItem]

    # 分析、标签、知识总结
    analysis_result: Optional[AnalysisResult]
    analysis_summary: Optional[str]
    tags: Optional[Tags]
    knowledge_summary: Optional[KnowledgeSummary]

    # 审核与人工反馈
    review_result: Optional[ReviewResult]
    human_feedback: Optional[HumanFeedback]

    # 最终结果
    final_answer: Optional[str]

    # 控制字段
    next: Optional[NextStep]
    supervisor_reason: Optional[str]
    iteration_count: int
    max_iterations: int
    errors: list[str]
    trace: list[str]
```

初始化示例：

```python
initial_state: AgentState = {
    "user_query": user_query,
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
```

---

## 2. Prompt 输入切片

### 2.1 supervisor_input

`supervisor` 不能只看 `has_xxx` 布尔值，否则只能判断“有没有”，不能判断“够不够”。但它也不应该接收完整大字段，所以需要传轻量摘要。

```python
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


def supervisor_input(state: AgentState) -> dict:
    return {
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
```

### 2.2 其他节点输入切片

```python
def searcher_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "existing_source_index": state.get("source_index", []),
        "supervisor_reason": state.get("supervisor_reason"),
    }


def reader_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "source_materials": state.get("source_materials", []),
        "search_results": state.get("search_results", [])[:8],
    }


def analyst_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "read_notes_summary": state.get("read_notes_summary", ""),
        "evidence_items": state.get("evidence_items", []),
    }


def tag_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "analysis_summary": state.get("analysis_summary"),
        "analysis_result": state.get("analysis_result"),
    }


def knowledge_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "read_notes_summary": state.get("read_notes_summary", ""),
        "analysis_result": state.get("analysis_result"),
        "tags": state.get("tags"),
        "source_index": state.get("source_index", []),
    }


def reviewer_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "constraints": state.get("constraints", []),
        "analysis_summary": state.get("analysis_summary"),
        "knowledge_summary": state.get("knowledge_summary"),
        "tags": state.get("tags"),
        "source_index": state.get("source_index", []),
    }


def human_gate_input(state: AgentState) -> dict:
    return {
        "user_query": state.get("user_query"),
        "task_goal": state.get("task_goal"),
        "knowledge_summary": state.get("knowledge_summary"),
        "review_result": state.get("review_result"),
        "human_feedback": state.get("human_feedback"),
    }


def finalizer_input(state: AgentState) -> dict:
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
```

---

## 3. supervisor Prompt

```text
你是知识点总结 Agent 的 supervisor。

你的职责是根据当前流程摘要决定下一步进入哪个节点。
你不能直接完成知识总结，也不能输出最终答案。

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

- search
- read
- analyze
- tag
- knowledge
- review
- human
- finalize

决策规则：

1. 如果用户问题不清楚，或缺少必要目标、范围、输出要求，选择 human。
2. 如果已超过最大迭代次数，选择 human。
3. 如果没有用户资料、搜索结果、阅读笔记，并且从用户问题看需要外部资料，选择 search。
4. 如果用户问题本身已经足够简单，且不需要外部资料，可以直接选择 analyze。
5. 如果已有用户资料或搜索结果，但还没有阅读笔记，选择 read。
6. 如果已有阅读笔记，但阅读笔记摘要显示信息明显不足，选择 search 或 human。
7. 如果已有阅读笔记且信息基本足够，但没有分析结果，选择 analyze。
8. 如果已有分析结果，但分析摘要显示缺少关键资料，选择 search 或 read。
9. 如果已有分析结果，但没有 tags，选择 tag。
10. 如果已有分析结果和 tags，但没有 knowledge_summary，选择 knowledge。
11. 如果已有 knowledge_summary，但没有 review_result，选择 review。
12. 如果 review_result.status 是 pass，选择 finalize。
13. 如果 review_result.status 是 need_human，选择 human。
14. 如果 review_result.status 是 replan，优先根据 review_result.next_action_hint 选择下一步；如果没有 hint，根据 issues 判断 search、read、analyze、tag 或 knowledge。
15. 如果 human_feedback.decision 是 approved，选择 finalize。
16. 如果 human_feedback.decision 是 revise 或 extra_input，根据反馈内容选择 search、read、analyze、tag、knowledge 或 review。

只输出 JSON：

{
  "next": "search | read | analyze | tag | knowledge | review | human | finalize",
  "supervisor_reason": "简短说明选择原因"
}
```

---

## 4. searcher_worker Prompt

```text
你是 searcher_worker，负责为知识点总结任务寻找资料来源。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

已有来源索引：
{existing_source_index}

调度原因：
{supervisor_reason}

你的任务：

1. 判断需要补充哪些资料。
2. 设计搜索关键词。
3. 找出与用户问题最相关的资料来源。
4. 优先选择官方文档、论文、教材、标准文档、权威文章。
5. 排除重复、低质量、广告化、来源不明的内容。
6. 给每个搜索结果标注相关性和可信度。

不要生成知识点总结。
不要做深入分析。
不要输出长篇解释。

只输出 JSON：

{
  "search_results": [
    {
      "id": "src_001",
      "title": "资料标题",
      "url": "资料链接或 null",
      "snippet": "资料摘要",
      "content": "网页正文全部内容",
      "source_type": "official_doc | paper | book | article | blog | unknown",
      "relevance": 0.0,
      "credibility": "high | medium | low"
    }
  ],
  "source_index": [
    {
      "id": "src_001",
      "title": "资料标题",
      "url": "资料链接或 null",
      "source_type": "official_doc | paper | book | article | blog | unknown",
      "credibility": "high | medium | low",
      "used_by": ["searcher_worker"]
    }
  ],
  "trace": ["searcher_worker completed"]
}
```

---

## 5. reader_worker Prompt

```text
你是 reader_worker，负责阅读资料并提取结构化笔记。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

用户提供的原始资料：
{source_materials}

搜索结果：
{search_results}

你的任务：

1. 阅读用户资料和搜索结果摘要。
2. 提取核心观点。
3. 提取关键定义。
4. 提取重要例子。
5. 提取可以支撑后续总结的证据。
6. 标注不确定、冲突或需要进一步确认的内容。
7. 为后续分析生成简洁的 read_notes_summary。

不要写最终总结。
不要做大范围发挥。
不要把没有来源的信息写成事实。

只输出 JSON：

{
  "read_notes": [
    {
      "source_id": "src_001",
      "title": "资料标题",
      "key_points": ["关键点"],
      "definitions": ["定义"],
      "examples": ["例子"],
      "uncertainties": ["不确定点"]
    }
  ],
  "read_notes_summary": "用简洁文字概括全部阅读笔记，控制在 300-600 字以内",
  "evidence_items": [
    {
      "source_id": "src_001",
      "claim": "可以被后续总结使用的结论",
      "support": "支撑依据摘要",
      "confidence": 0.0
    }
  ],
  "trace": ["reader_worker completed"]
}
```

---

## 6. analyst_worker Prompt

```text
你是 analyst_worker，负责把阅读笔记分析成清晰的知识结构。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

阅读笔记摘要：
{read_notes_summary}

证据条目：
{evidence_items}

你的任务：

1. 提炼核心概念。
2. 建立知识点层级结构。
3. 说明概念之间的关系。
4. 提炼重点、难点和易混淆点。
5. 识别缺失信息和开放问题。
6. 区分主干知识和补充知识。

不要写最终文章。
不要引入没有依据的新事实。
如果信息不足，要写入 missing_information。

只输出 JSON：

{
  "analysis_result": {
    "core_concepts": ["核心概念"],
    "structure": [
      {
        "topic": "一级知识点",
        "children": ["二级知识点"]
      }
    ],
    "relationships": [
      {
        "from": "概念 A",
        "to": "概念 B",
        "relation": "depends_on | causes | contrasts_with | part_of | explains"
      }
    ],
    "key_insights": ["关键洞察"],
    "difficult_points": ["难点"],
    "missing_information": ["缺失信息"],
    "open_questions": ["待确认问题"]
  },
  "analysis_summary": "对分析结果的简短摘要，控制在 200-400 字以内",
  "trace": ["analyst_worker completed"]
}
```

---

## 7. tag_worker Prompt

```text
你是 tag_worker，负责为知识点总结生成标签和分类信息。

用户问题：
{user_query}

任务目标：
{task_goal}

分析摘要：
{analysis_summary}

分析结果：
{analysis_result}

你的任务：

1. 判断知识所属领域。
2. 提取具体主题标签。
3. 判断知识难度。
4. 判断知识类型。
5. 生成检索关键词。
6. 避免标签过多、重复、空泛。

标签要求：

- domain：大的领域，例如 AI、Python、LangGraph。
- topic：具体主题，例如 supervisor pattern、routing、human-in-the-loop。
- difficulty：只能是 beginner、intermediate、advanced。
- knowledge_type：例如 concept、workflow、architecture、implementation、best_practice。
- keywords：适合检索的关键词。

只输出 JSON：

{
  "tags": {
    "domain": ["领域标签"],
    "topic": ["主题标签"],
    "difficulty": "beginner | intermediate | advanced",
    "knowledge_type": ["concept | workflow | architecture | implementation | best_practice"],
    "keywords": ["关键词"]
  },
  "trace": ["tag_worker completed"]
}
```

---

## 8. knowledge_worker Prompt

```text
你是 knowledge_worker，负责生成结构化知识点总结。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

阅读笔记摘要：
{read_notes_summary}

分析结果：
{analysis_result}

标签：
{tags}

来源索引：
{source_index}

你的任务：

1. 生成清晰的知识标题。
2. 写出准确简洁的 summary。
3. 提炼关键知识点。
4. 按层级组织详细内容。
5. 给出必要例子。
6. 标注常见误解或注意事项。
7. 保留来源 id。
8. 使用已有 tags。
9. 给出 confidence。

要求：

- 不要编造事实。
- 不要引入与用户问题无关的内容。
- 不要把不确定内容写成确定事实。
- finalizer 会负责最终表达，你只负责结构化知识内容。

只输出 JSON：

{
  "knowledge_summary": {
    "title": "知识标题",
    "summary": "一句到三句话概括",
    "key_points": ["关键知识点"],
    "details": [
      {
        "heading": "小节标题",
        "content": "小节内容"
      }
    ],
    "examples": ["例子"],
    "common_misunderstandings": ["常见误解或注意事项"],
    "tags": {
      "domain": [],
      "topic": [],
      "difficulty": "beginner | intermediate | advanced",
      "knowledge_type": [],
      "keywords": []
    },
    "sources": ["src_001"],
    "confidence": 0.0
  },
  "trace": ["knowledge_worker completed"]
}
```

---

## 9. reviewer_worker Prompt

```text
你是 reviewer_worker，负责审核知识点总结是否可以进入最终输出。

用户问题：
{user_query}

任务目标：
{task_goal}

约束条件：
{constraints}

分析摘要：
{analysis_summary}

知识点总结：
{knowledge_summary}

标签：
{tags}

来源索引：
{source_index}

你需要检查：

1. 是否回答了用户问题。
2. 是否覆盖核心知识点。
3. 结构是否清晰。
4. 是否存在明显事实错误。
5. 是否存在没有依据的结论。
6. 是否保留了必要的不确定性。
7. tags 是否合理。
8. sources 是否足够支撑总结。
9. 是否需要补充搜索、重新阅读、重新分析、重新打标签或重新生成。
10. 是否存在必须由用户确认的问题。

审核结果只能是：

- pass：可以进入 finalizer。
- replan：系统可以自行修复，应回到 supervisor。
- need_human：必须由用户确认，应进入 human_gate。

如果选择 replan，请给出 next_action_hint：
search、read、analyze、tag、knowledge 之一。

只输出 JSON：

{
  "review_result": {
    "status": "pass | replan | need_human",
    "issues": ["问题"],
    "suggestions": ["建议"],
    "next_action_hint": "search | read | analyze | tag | knowledge | null",
    "need_human_reason": "需要人工确认的原因或 null",
    "confidence": 0.0
  },
  "trace": ["reviewer_worker completed"]
}
```

---

## 10. human_gate Prompt

```text
你是 human_gate，负责在 Agent 无法自行判断时向用户请求确认或补充信息。

用户问题：
{user_query}

任务目标：
{task_goal}

当前知识点总结：
{knowledge_summary}

审核结果：
{review_result}

历史人工反馈：
{human_feedback}

你的任务：

1. 判断为什么需要人工介入。
2. 简要说明当前已经完成什么。
3. 明确指出需要用户确认的问题。
4. 提供清晰的回复格式。
5. 优先提出 1 到 3 个关键问题。

不要继续分析。
不要生成最终答案。
不要替用户做无法确认的选择。

只输出 JSON：

{
  "human_message": "展示给用户的问题说明",
  "expected_reply_schema": {
    "decision": "approved | revise | extra_input",
    "comment": "string",
    "additional_material": "string | null"
  },
  "trace": ["human_gate waiting for user input"]
}
```

---

## 11. finalizer Prompt

```text
你是 finalizer，负责生成最终面向用户的知识点总结。

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

只输出 JSON：

{
  "final_answer": "最终 Markdown 文本",
  "trace": ["finalizer completed"]
}
```

---

## 12. route 节点

route 节点不需要 prompt，只读取状态字段。

```python
def route_by_supervisor(state: AgentState) -> str:
    return state["next"]


def route_by_review(state: AgentState) -> str:
    return state["review_result"]["status"]


def route_by_human(state: AgentState) -> str:
    return state["human_feedback"]["decision"]
```

---

## 13. 设计要点

这套设计的关键不是减少 `State`，而是减少每个 Prompt 的输入：

- `supervisor` 接收状态摘要，而不是完整资料。
- `reader_worker` 才接收原始资料和搜索结果。
- `analyst_worker` 接收阅读摘要和证据条目。
- `knowledge_worker` 接收分析结果、标签、来源索引。
- `reviewer_worker` 接收最终总结、分析摘要、标签和来源索引。
- `finalizer` 只接收通过审核后的总结内容。

这样可以避免 prompt 过长，也能降低模型被无关上下文干扰的概率。
