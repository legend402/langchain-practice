from dataclasses import dataclass
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
    "supervisor",
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
    messages: list[(str, str)]
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


@dataclass
class DocumentElement:
    """
    文档元素中间表示。
    由 parser 单次遍历 DoclingDocument 产出，chunker 基于此做分块。
    参数:
        element_type: 元素类型（heading / paragraph / table / image / code）
        text: 文本内容（表格为 Markdown，图片为描述文本）
        page_number: 所在页码
        heading_level: 标题层级（仅 heading 类型有效，1=H1, 2=H2...）
        table_id: 表格唯一标识（仅 table 类型，如 T-001）
    """

    element_type: str
    text: str
    page_number: int
    heading_level: int = 0
    table_id: Optional[str] = None


@dataclass
class ChunkConfig:
    """
    结构化分块配置。
    参数:
        max_chunk_size: 最大字符数
        chunk_overlap: 重叠字符数（仅段落间）
        keep_table_intact: 表格是否不拆分
        merge_short_paragraphs: 是否合并短段落
    """

    max_chunk_size: int = 1000
    chunk_overlap: int = 100
    keep_table_intact: bool = True
    merge_short_paragraphs: bool = True


@dataclass
class StructuredChunk:
    """
    结构化分块结果。
    参数:
        text: chunk 文本内容
        chunk_index: chunk 序号
        page_start: 起始页码
        page_end: 结束页码
        heading_path: 标题路径列表
        content_type: 内容类型（text/table/image/code）
        table_id: 表格唯一标识（如有）
        position: 文档内位置序号
    """

    text: str
    chunk_index: int
    page_start: int
    page_end: int
    heading_path: list[str]
    content_type: str
    table_id: Optional[str] = None
    position: int = 0


PARSE_TASK_KEY_PREFIX = "parse_task:"
PARSE_TASK_TTL = 3600

ParseTaskStatus = Literal[
    "pending",
    "parsing",
    "enriching_images",
    "walking_cache",
    "chunking",
    "embedding",
    "storing",
    "completed",
    "failed",
]
