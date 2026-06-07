"""
文档表格抽取工具。
从解析缓存中读取表格 Markdown 内容，支持按页码或关键词筛选。
"""

from langchain_community.tools import tool


@tool
async def extract_tables(
    entry_id: str,
    page_number: int | None = None,
    keyword: str | None = None,
) -> str:
    """
    从文档中抽取表格（Markdown 格式）。
    当需要查看文档中的数据表格、统计信息、对比数据时调用。
    :entry_id str: 知识条目 ID
    :page_number int: 指定页码的表格（可选）
    :keyword str: 按关键词匹配表格标题或上下文（可选）
    """
    import json
    import os
    from pathlib import Path

    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    tables_dir = Path(upload_dir) / "parsed" / entry_id / "tables"

    if not tables_dir.exists():
        return f"文档缓存不存在: {entry_id}"

    meta_file = tables_dir / "tables_meta.json"
    if not meta_file.exists():
        return "未找到表格元数据"

    tables_meta = json.loads(meta_file.read_text(encoding="utf-8"))
    if not tables_meta:
        return "文档中无表格"

    filtered = tables_meta
    if page_number is not None:
        filtered = [t for t in filtered if t.get("page_number") == page_number]
    if keyword:
        keyword_lower = keyword.lower()
        filtered = [
            t for t in filtered
            if keyword_lower in t.get("heading", "").lower()
        ]

    if not filtered:
        hint = f"第 {page_number} 页" if page_number else f"关键词 '{keyword}'"
        return f"未找到{hint}相关的表格"

    results = []
    for t in filtered:
        table_file = tables_dir / f"{t['table_id']}.md"
        if table_file.exists():
            content = table_file.read_text(encoding="utf-8")
            page_info = f"第{t.get('page_number', '?')}页"
            results.append(f"--- {t['table_id']} ({page_info}) ---\n{content}")

    if not results:
        return "表格文件读取失败"

    return "\n\n".join(results)
