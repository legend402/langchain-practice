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
    "supervisor"
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
