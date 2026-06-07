import os
import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from dataclasses import dataclass

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.knowledge.chunker import chunk_structured
from src.knowledge.embedding import aembed_texts
from src.knowledge.milvus import (
    delete_entry_chunks,
    get_milvus_client,
    get_or_create_collection,
    delete_v2_entry_chunks,
    get_or_create_v2_collection,
)
from src.knowledge.search import SearchHit, StructuredSearchHit, hybrid_search, hybrid_search_v2
from src.service.db.db import KnowledgeEntry
from src.utils.pagination import PaginatedResult, pagination
from src.utils.reader import read

logger = logging.getLogger(__name__)


@dataclass
class _SimpleChunk:
    """v1 兼容的简单分块结果。"""
    text: str
    index: int


def _chunk_text(text: str, title: str = "", chunk_size: int = 800, overlap: int = 200) -> list[_SimpleChunk]:
    """
    v1 兼容的简单递归字符分块。
    参数:
        text: 待分块文本
        title: 标题（拼到每个 chunk 开头）
        chunk_size: 最大字符数
        overlap: 重叠字符数
    返回:
        _SimpleChunk 列表
    """
    if not text.strip():
        return []
    prefix = f"# {title}\n\n" if title else ""
    step = max(1, chunk_size - overlap)
    chunks = []
    for i, start in enumerate(range(0, len(text), step)):
        segment = text[start : start + chunk_size]
        if segment.strip():
            chunks.append(_SimpleChunk(text=prefix + segment, index=i))
    return chunks

async def save_entry(
  session: AsyncSession,
  user_id: UUID,
  title: str,
  content: str | None = None,
  file_id: str | None = None,
  source_type: str = "manual",
  source_id: str | None = None,
) -> KnowledgeEntry:
  """
    存入知识条目。
    根据 source_type 获取文本，分块、向量化后存入 Milvus，并写 PG 元数据。
    参数:
        session: 数据库会话
        user_id: 用户 ID
        title: 知识标题
        content: 直接传入的文本内容
        file_id: 文件上传记录 ID
        source_type: 来源类型（research/manual/file）
        source_id: 关联来源 ID
    返回:
        KnowledgeEntry 数据库记录
  """
  text = content or ""
  if file_id and not text:
    from src.service.controller.FileUpload import get_file_record
    record = await get_file_record(session, file_id)
    if record:
      text = read(record.file_path)
  
  chunks: list[_SimpleChunk] = _chunk_text(text, title=title)
  uid = str(user_id)
  col_name = get_or_create_collection(uid)
  client = get_milvus_client()

  chunk_texts = [c.text for c in chunks]
  vectors = await aembed_texts(chunk_texts)

  entry_id = str(uuid4())

  data = []

  for chunk, vector in zip(chunks, vectors):
    data.append({
      "entry_id": entry_id,
      "chunk_index": chunk.index,
      "text": chunk.text,
      "dense_vector": vector,
    })

  client.insert(collection_name=col_name, data=data)

  preview = (text[:200] + "...") if len(text) > 200 else text
  entry = KnowledgeEntry(
    id=entry_id,
    user_id=user_id,
    title=title,
    source_type=source_type,
    source_id=source_id or file_id,
    chunk_count=len(chunks),
    content_preview=preview,
  )
  session.add(entry),
  await session.commit()
  await session.refresh(entry)
  return entry

async def delete_entry(
    session: AsyncSession,
    user_id: UUID,
    entry_id: str,
) -> bool:
  """
  删除知识条目。同时删除 Milvus 中的 chunks 和 PG 记录。
  参数:
      session: 数据库会话
      user_id: 用户 ID
      entry_id: 知识条目 ID
  返回:
      是否删除成功
  """
  entry = await session.get(KnowledgeEntry, entry_id)
  if not entry or str(entry.user_id) != str(user_id):
      return False

  delete_entry_chunks(str(user_id), entry_id)
  await session.delete(entry)
  await session.commit()
  return True

async def list_entries(
    session: AsyncSession,
    user_id: UUID,
    page: int = 1,
    size: int = 20,
) -> PaginatedResult[KnowledgeEntry]:
  """
  获取用户的知识条目列表（分页）。使用通用 paginate 工具。
  参数:
      session: 数据库会话
      user_id: 用户 ID
      page: 页码（从 1 开始）
      size: 每页数量
  返回:
      PaginatedResult[KnowledgeEntry] 分页结果
  """
  return await pagination(
      session,
      KnowledgeEntry,
      user_id=user_id,
      page=page,
      size=size,
      order_attr="create_at",
      descending=True,
  )

async def search_knowledge(
    user_id: UUID,
    query: str,
    top_k: int = 5,
) -> list[SearchHit]:
  """
  检索用户知识库。
  参数:
      user_id: 用户 ID
      query: 查询文本
      top_k: 返回结果数量
  返回:
      SearchHit 列表
  """
  return hybrid_search(query, str(user_id), top_k)


async def search_entries(
    session: AsyncSession,
    user_id: UUID,
    query: str,
    top_k: int = 5,
) -> list[KnowledgeEntry]:
  """
  检索用户知识库并返回去重后的 entry 列表。
  参数:
      session: 数据库会话
      user_id: 用户 ID
      query: 查询文本
      top_k: 搜索 chunk 数量
  返回:
      KnowledgeEntry 列表（按首次出现顺序排列）
  """
  hits = hybrid_search(query, str(user_id), top_k)
  seen: set[str] = set()
  entry_ids: list[str] = []
  for h in hits:
    if h.entry_id not in seen:
      seen.add(h.entry_id)
      entry_ids.append(h.entry_id)
  if not entry_ids:
    return []
  result = await session.exec(
    select(KnowledgeEntry)
    .where(KnowledgeEntry.id.in_(entry_ids), KnowledgeEntry.user_id == user_id)
  )
  entry_map = {str(e.id): e for e in result.all()}
  return [entry_map[eid] for eid in entry_ids if eid in entry_map]


async def save_entry_v2(
    session: AsyncSession,
    user_id: UUID,
    title: str,
    file_id: str | None = None,
    content: str | None = None,
    source_type: str = "file",
    source_id: str | None = None,
) -> KnowledgeEntry:
    """
    v2 知识条目存入：Docling 解析 → 结构化分块 → 向量化 → Milvus v2。
    参数:
        session: 数据库会话
        user_id: 用户 ID
        title: 知识标题
        file_id: 文件上传记录 ID
        content: 直接传入的文本内容（无文件时使用）
        source_type: 来源类型
        source_id: 关联来源 ID
    返回:
        KnowledgeEntry 数据库记录
    """
    from src.knowledge.parser import parse_document
    from src.knowledge.chunker import chunk_structured

    entry_id = str(uuid4())
    uid = str(user_id)
    col_name = get_or_create_v2_collection(uid)
    client = get_milvus_client()

    if file_id:
        from src.service.controller.FileUpload import get_file_record
        record = await get_file_record(session, file_id)
        if not record:
            raise FileNotFoundError(f"文件记录不存在: {file_id}")

        parsed = await parse_document(record.file_path, entry_id)
        chunks = chunk_structured(parsed.elements)

        chunk_texts = [c.text for c in chunks]
        preview = (chunk_texts[0][:200] + "...") if chunk_texts and len(chunk_texts[0]) > 200 else (chunk_texts[0] if chunk_texts else "")
    elif content:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(content)
            tmp_path = f.name

        try:
            parsed = await parse_document(tmp_path, entry_id)
            chunks = chunk_structured(parsed.elements)
        finally:
            os.unlink(tmp_path)

        chunk_texts = [c.text for c in chunks]
        preview = (content[:200] + "...") if len(content) > 200 else content
    else:
        raise ValueError("file_id 或 content 必须提供其一")

    vectors = await aembed_texts(chunk_texts)

    data = []
    for chunk, vector in zip(chunks, vectors):
        data.append({
            "entry_id": entry_id,
            "chunk_index": chunk.chunk_index,
            "text": chunk.text,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "heading_path": json.dumps(chunk.heading_path, ensure_ascii=False),
            "content_type": chunk.content_type,
            "table_id": chunk.table_id or "",
            "dense_vector": vector,
        })

    client.insert(collection_name=col_name, data=data)

    entry = KnowledgeEntry(
        id=entry_id,
        user_id=user_id,
        title=title,
        source_type=source_type,
        source_id=source_id or file_id,
        chunk_count=len(chunks),
        content_preview=preview,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def delete_entry_v2(
    session: AsyncSession,
    user_id: UUID,
    entry_id: str,
) -> bool:
    """
    v2 删除知识条目。同时删除 Milvus v2 chunks、缓存文件和 PG 记录。
    参数:
        session: 数据库会话
        user_id: 用户 ID
        entry_id: 知识条目 ID
    返回:
        是否删除成功
    """
    entry = await session.get(KnowledgeEntry, entry_id)
    if not entry or str(entry.user_id) != str(user_id):
        return False

    delete_v2_entry_chunks(str(user_id), entry_id)

    cache_dir = Path(os.getenv("UPLOAD_DIR", "./uploads")) / "parsed" / entry_id
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir, ignore_errors=True)

    await session.delete(entry)
    await session.commit()
    return True


async def search_knowledge_v2(
    user_id: UUID,
    query: str,
    top_k: int = 5,
) -> list[StructuredSearchHit]:
    """
    v2 检索用户知识库，返回带元数据的结果。
    参数:
        user_id: 用户 ID
        query: 查询文本
        top_k: 返回结果数量
    返回:
        StructuredSearchHit 列表
    """
    return hybrid_search_v2(query, str(user_id), top_k)
