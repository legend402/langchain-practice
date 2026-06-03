from uuid import UUID, uuid4
from sqlmodel.ext.asyncio.session import AsyncSession
from src.knowledge.chunker import Chunk, chunk_text
from src.knowledge.embedding import aembed_texts
from src.knowledge.milvus import delete_entry_chunks, get_milvus_client, get_or_create_collection
from src.knowledge.search import SearchHit, hybrid_search
from src.service.db.db import KnowledgeEntry
from src.utils.pagination import PaginatedResult, pagination
from src.utils.reader import read


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
  
  chunks: list[Chunk] = chunk_text(text, title=title)
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
  await session.refresh()
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
