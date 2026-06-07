"""
按页码读取文档原文工具。
从 full.md 缓存中读取完整文档内容。
"""

from langchain_community.tools import tool


@tool
async def read_pages(entry_id: str) -> str:
    """
    读取指定文档的完整原文内容（Markdown 格式）。
    当需要查看文档的完整上下文、验证检索结果或获取更多细节时调用。
    :entry_id str: 知识条目 ID
    """
    import os
    from pathlib import Path

    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    full_md = Path(upload_dir) / "parsed" / entry_id / "full.md"

    if not full_md.exists():
        return f"文档缓存不存在: {entry_id}"

    return full_md.read_text(encoding="utf-8")
