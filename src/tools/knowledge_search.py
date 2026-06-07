"""
知识库语义检索工具（v2 版本）。
返回带页码、章节等溯源信息的检索结果。
"""

from langchain_community.tools import tool


@tool
async def knowledge_search(query: str) -> str:
    """
    知识库检索工具。当用户的问题可能命中已有知识库内容时调用。
    使用 dense + BM25 混合检索，返回带溯源信息的知识片段。
    回答时请附注来源，格式：（来源：《文档标题》第X页 "章节名"）
    :query str: 检索查询文本
    """
    from src.knowledge.search import hybrid_search_v2
    from src.utils.agent import get_current_user_id

    user_id = get_current_user_id()
    if not user_id:
        return "无法获取用户信息"

    hits = hybrid_search_v2(query, user_id, top_k=5)
    if not hits:
        return "知识库中未找到相关内容"

    results = []
    for h in hits:
        pages = f"第{h.page_start}" if h.page_start == h.page_end else f"第{h.page_start}-{h.page_end}页"
        heading = " > ".join(h.heading_path) if h.heading_path else ""
        source_info = f"{pages}"
        if heading:
            source_info += f' "{heading}"'
        if h.table_id:
            source_info += f" {h.table_id}"

        results.append(
            f"[来源 {source_info}] (相关度: {h.score:.4f})\n{h.text}"
        )
    return "\n\n---\n\n".join(results)
