# 知识库功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为问答系统接入用户独立知识库，支持 research 结果/文件上传/手动文本三种存入方式，使用 Milvus + GLM embedding-3 + BM25 混合检索。

**Architecture:** 在后端新增 `knowledge/` 核心模块封装 Milvus 操作和 Embedding 调用，Chat Agent 新增 `knowledge_search`、`read_file`、`save_to_knowledge` 三个工具；前端新增知识库管理页面和文件上传功能。

**Tech Stack:** pymilvus、zhipuai (langchain_community.embeddings.ZhipuAIEmbeddings)、FastAPI、SQLModel、React 19、Tailwind CSS v4、lucide-react、@headlessui/react

---

## File Structure

### 后端新增文件

| 文件                                         | 职责                                         |
| -------------------------------------------- | -------------------------------------------- |
| `src/knowledge/__init__.py`                | 模块导出                                     |
| `src/knowledge/embedding.py`               | GLM embedding-3 封装（同步/异步 embed）      |
| `src/knowledge/chunker.py`                 | 递归字符分块器                               |
| `src/knowledge/milvus.py`                  | Milvus 连接管理、Collection Schema、索引创建 |
| `src/knowledge/search.py`                  | 混合检索（dense + BM25 + RRFRanker）         |
| `src/knowledge/service.py`                 | 知识库 CRUD 业务逻辑                         |
| `src/tools/knowledge_search.py`            | Chat Agent 知识库检索 @tool                  |
| `src/tools/read_file.py`                   | Chat Agent 文件读取 @tool                    |
| `src/tools/save_to_knowledge.py`           | Chat Agent 存入知识库 @tool                  |
| `src/service/controller/FileUpload.py`     | 文件上传 CRUD                                |
| `src/service/controller/KnowledgeEntry.py` | 知识条目 CRUD                                |
| `src/service/routes/upload.py`             | /upload/* 路由                               |
| `src/service/routes/knowledge.py`          | /knowledge/* 路由                            |
| `src/utils/pagination.py`                  | 通用后端分页工具函数                         |

### 后端修改文件

| 文件                               | 改动                                                    |
| ---------------------------------- | ------------------------------------------------------- |
| `src/service/db/db.py`           | 新增 FileUpload、KnowledgeEntry 表模型                  |
| `src/service/db/database.py`     | import 新表模型                                         |
| `src/service/__init__.py`        | lifespan 中初始化 Milvus、注册新路由、创建 uploads 目录 |
| `src/agent/chat/config.py`       | ChatState 新增 file_ids 字段                            |
| `src/agent/chat/create_agent.py` | 工具列表扩展                                            |
| `src/agent/chat/nodes/chat.py`   | 系统提示词更新                                          |
| `src/service/routes/chat.py`     | ChatStart 新增 file_ids 字段                            |
| `requirements.txt`               | 新增 pymilvus、zhipuai、charset-normalizer、PyPDF2      |
| `.env.example`                   | 新增 MILVUS_URI、ZHIPU_API_KEY、UPLOAD_DIR              |

### 前端新增文件

| 文件                                                   | 职责                                               |
| ------------------------------------------------------ | -------------------------------------------------- |
| `frontend/src/types/knowledge.ts`                    | 知识库/文件上传类型定义                            |
| `frontend/src/api/uploadApi.ts`                      | 文件上传 API                                       |
| `frontend/src/api/knowledgeApi.ts`                   | 知识库 API                                         |
| `frontend/src/components/Modal.tsx`                  | 通用 Modal 壳组件（基于 @headlessui/react Dialog） |
| `frontend/src/components/FileUploader.tsx`           | 通用文件上传组件                                   |
| `frontend/src/components/Pagination.tsx`             | 通用分页组件                                       |
| `frontend/src/hooks/usePagination.ts`                | 通用分页 hook                                      |
| `frontend/src/pages/knowledge/KnowledgePage.tsx`     | 知识库管理页面                                     |
| `frontend/src/pages/knowledge/AddKnowledgeModal.tsx` | 新增知识业务弹窗                                   |

### 前端修改文件

| 文件                                           | 改动                        |
| ---------------------------------------------- | --------------------------- |
| `frontend/src/types/agent.ts`                | SubmitRequest 新增 file_ids |
| `frontend/src/routes/index.tsx`              | 新增 /knowledge 路由        |
| `frontend/src/components/SessionSidebar.tsx` | 新增"知识库"导航入口        |
| `frontend/src/components/ResultCard.tsx`     | 新增"存入知识库"按钮        |
| `frontend/src/pages/chat/ChatPage.tsx`       | 搜索框新增附件上传按钮      |
| `frontend/src/hooks/useAgentChat.ts`         | submit 支持 file_ids 参数   |

---

### Task 1: 依赖安装与环境变量

**Files:**

- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: 更新 requirements.txt**

在文件末尾追加：

```
pymilvus
zhipuai
charset-normalizer
PyPDF2
```

- [ ] **Step 2: 更新 .env.example**

在末尾追加：

```
MILVUS_URI=http://localhost:19530
ZHIPU_API_KEY=YOUR_ZHIPU_API_KEY
UPLOAD_DIR=./uploads
```

- [ ] **Step 3: 安装后端依赖**

Run: `pip install pymilvus zhipuai charset-normalizer PyPDF2`

- [ ] **Step 4: 安装前端依赖**

Run: `cd frontend && npm install @headlessui/react`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example frontend/package.json frontend/package-lock.json
git commit -m "chore: 新增知识库功能依赖和环境变量配置"
```

---

### Task 2: 后端 — 数据库表模型

**Files:**

- Modify: `src/service/db/db.py`
- Modify: `src/service/db/database.py`

- [ ] **Step 1: 在 db.py 中新增 FileUpload 和 KnowledgeEntry 表**

在文件末尾追加：

```python
class FileUpload(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="fullauth_users.id")
    file_name: str
    file_path: str
    file_format: str
    file_size: int
    create_at: datetime = Field(default_factory=datetime.now)


class KnowledgeEntry(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="fullauth_users.id")
    title: str
    source_type: str
    source_id: Optional[str] = None
    chunk_count: int = 0
    content_preview: Optional[str] = None
    create_at: datetime = Field(default_factory=datetime.now)
```

需要在文件顶部 import 中补充 `from uuid import uuid4`。

- [ ] **Step 2: 在 database.py 中 import 新表**

修改 `src/service/db/database.py` 第 5 行：

```python
from src.service.db.db import ChatMessage, ChatSession, FileUpload, KnowledgeEntry
```

- [ ] **Step 3: 启动应用验证表创建**

Run: `python -c "from src.service.db.db import FileUpload, KnowledgeEntry; print('OK')"`

Expected: OK

- [ ] **Step 4: Commit**

```bash
git add src/service/db/db.py src/service/db/database.py
git commit -m "feat: 新增 FileUpload 和 KnowledgeEntry 数据库表模型"
```

---

### Task 3: 后端 — Embedding 封装

**Files:**

- Create: `src/knowledge/__init__.py`
- Create: `src/knowledge/embedding.py`

- [ ] **Step 1: 创建 `src/knowledge/__init__.py`**

空文件。

- [ ] **Step 2: 创建 `src/knowledge/embedding.py`**

```python
import os
from langchain_community.embeddings import ZhipuAIEmbeddings

_embeddings: ZhipuAIEmbeddings | None = None


def get_embeddings() -> ZhipuAIEmbeddings:
    """
    获取 ZhipuAIEmbeddings 单例。
    使用 embedding-3 模型，维度 2048。
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = ZhipuAIEmbeddings(
            model="embedding-3",
            api_key=os.getenv("ZHIPU_API_KEY"),
        )
    return _embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    批量文本向量化。
    参数:
        texts: 待编码的文本列表
    返回:
        向量列表，每个向量维度为 2048
    """
    return get_embeddings().embed_documents(texts)


async def aembed_texts(texts: list[str]) -> list[list[float]]:
    """
    异步批量文本向量化。
    参数:
        texts: 待编码的文本列表
    返回:
        向量列表，每个向量维度为 2048
    """
    return await get_embeddings().aembed_documents(texts)


def embed_query(text: str) -> list[float]:
    """
    单条查询文本向量化。
    参数:
        text: 查询文本
    返回:
        向量，维度为 2048
    """
    return get_embeddings().embed_query(text)


async def aembed_query(text: str) -> list[float]:
    """
    异步单条查询文本向量化。
    参数:
        text: 查询文本
    返回:
        向量，维度为 2048
    """
    return await get_embeddings().aembed_query(text)
```

- [ ] **Step 3: Commit**

```bash
git add src/knowledge/
git commit -m "feat: 新增 GLM embedding-3 封装模块"
```

---

### Task 4: 后端 — 文本分块器

**Files:**

- Create: `src/knowledge/chunker.py`

- [ ] **Step 1: 创建 chunker.py**

```python
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    index: int


def chunk_text(
    content: str,
    title: str = "",
    chunk_size: int = 800,
    overlap: int = 200,
) -> list[Chunk]:
    """
    递归字符分块器，支持重叠。
    将 title + content 按段落、行、字符优先级分割，每个 chunk 开头拼接 title。
    相邻块之间有 overlap 字符的重叠，确保跨块上下文连续。
    参数:
        content: 待分块的原始文本
        title: 知识标题，拼接到每个 chunk 开头
        chunk_size: 每块最大字符数
        overlap: 相邻块重叠字符数
    返回:
        Chunk 列表，包含 text 和 index
    """
    full_text = f"{title}\n\n{content}" if title else content
    if len(full_text) <= chunk_size:
        return [Chunk(text=full_text, index=0)]
    chunks: list[str] = []
    _recursive_split(full_text, chunk_size, overlap, chunks)
    result: list[Chunk] = []
    for i, text in enumerate(chunks):
        result.append(Chunk(text=text, index=i))
    return result


def _recursive_split(
    text: str, chunk_size: int, overlap: int, chunks: list[str]
) -> None:
    """
    递归分割文本。优先按 \\n\\n 分，再按 \\n 分，最后按字符分。
    """
    if len(text) <= chunk_size:
        chunks.append(text)
        return
    separators = ["\n\n", "\n"]
    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            _merge_parts(parts, sep, chunk_size, overlap, chunks)
            return
    _split_by_chars(text, chunk_size, overlap, chunks)


def _merge_parts(
    parts: list[str],
    sep: str,
    chunk_size: int,
    overlap: int,
    chunks: list[str],
) -> None:
    """
    将分割后的段落合并为不超过 chunk_size 的块。
    块之间保留 overlap 字符的重叠。
    """
    current = ""
    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                _recursive_split(current, chunk_size, overlap, chunks)
                overlap_text = current[-overlap:] if overlap < len(current) else current
                current = overlap_text + sep + part
            else:
                current = part
            if len(current) > chunk_size:
                _recursive_split(current, chunk_size, overlap, chunks)
                last_chunk = chunks[-1] if chunks else ""
                current = last_chunk[-overlap:] if overlap < len(last_chunk) else last_chunk
                if not current:
                    current = part
    if current and len(current) <= chunk_size:
        chunks.append(current)
    elif current:
        _recursive_split(current, chunk_size, overlap, chunks)


def _split_by_chars(
    text: str, chunk_size: int, overlap: int, chunks: list[str]
) -> None:
    """
    按固定字符数分割文本，步长为 chunk_size - overlap。
    """
    step = max(1, chunk_size - overlap)
    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size]
        if chunk:
            chunks.append(chunk)
```

- [ ] **Step 2: Commit**

```bash
git add src/knowledge/chunker.py
git commit -m "feat: 新增递归字符分块器"
```

---

### Task 5: 后端 — Milvus 连接管理

**Files:**

- Create: `src/knowledge/milvus.py`

- [ ] **Step 1: 创建 milvus.py**

```python
import os
from pymilvus import (
    MilvusClient,
    CollectionSchema,
    FieldSchema,
    DataType,
    Function,
    FunctionType,
)


MILVUS_URI = os.getenv("MILVUS_URI", "http://localhost:19530")
DENSE_DIM = 2048

_client: MilvusClient | None = None


def get_milvus_client() -> MilvusClient:
    """
    获取 MilvusClient 单例。
    """
    global _client
    if _client is None:
        _client = MilvusClient(uri=MILVUS_URI)
    return _client


def _collection_name(user_id: str) -> str:
    """
    根据用户 ID 生成 collection 名称。
    """
    return f"knowledge_{user_id.replace('-', '_')}"


def get_or_create_collection(user_id: str) -> str:
    """
    获取或创建用户的知识库 collection，返回 collection 名称。
    Schema 包含 dense_vector（embedding-3）和 sparse_vector（BM25 自动生成）。
    """
    client = get_milvus_client()
    col_name = _collection_name(user_id)

    if client.has_collection(col_name):
        return col_name

    schema = CollectionSchema(fields=[
        FieldSchema(
            name="pk",
            dtype=DataType.VARCHAR,
            is_primary=True,
            auto_id=True,
            max_length=100,
        ),
        FieldSchema(
            name="entry_id",
            dtype=DataType.VARCHAR,
            max_length=100,
        ),
        FieldSchema(
            name="chunk_index",
            dtype=DataType.INT32,
        ),
        FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=65535,
            enable_analyzer=True,
        ),
        FieldSchema(
            name="dense_vector",
            dtype=DataType.FLOAT_VECTOR,
            dim=DENSE_DIM,
        ),
        FieldSchema(
            name="sparse_vector",
            dtype=DataType.SPARSE_FLOAT_VECTOR,
        ),
    ])

    bm25_function = Function(
        name="text_bm25",
        input_field_names=["text"],
        output_field_names=["sparse_vector"],
        function_type=FunctionType.BM25,
    )
    schema.add_function(bm25_function)

    client.create_collection(collection_name=col_name, schema=schema)

    client.create_index(
        collection_name=col_name,
        field_name="dense_vector",
        index_params={"index_type": "AUTOINDEX", "metric_type": "IP"},
    )
    client.create_index(
        collection_name=col_name,
        field_name="sparse_vector",
        index_params={
            "index_type": "SPARSE_INVERTED_INDEX",
            "metric_type": "BM25",
            "params": {"inverted_index_algo": "DAAT_MAXSCORE"},
        },
    )
    client.load_collection(col_name)

    return col_name


def delete_entry_chunks(user_id: str, entry_id: str) -> None:
    """
    删除指定知识条目的所有 chunks。
    """
    client = get_milvus_client()
    col_name = _collection_name(user_id)
    if not client.has_collection(col_name):
        return
    client.delete(
        collection_name=col_name,
        filter=f'entry_id == "{entry_id}"',
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/knowledge/milvus.py
git commit -m "feat: 新增 Milvus 连接管理和 Collection 自动创建"
```

---

### Task 6: 后端 — 通用分页工具

**Files:**

- Create: `src/utils/pagination.py`

- [ ] **Step 1: 创建通用分页工具函数**

```python
from dataclasses import dataclass
from typing import TypeVar, Generic
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func

T = TypeVar("T", bound=SQLModel)


@dataclass
class PaginatedResult(Generic[T]):
    """
    通用分页结果。
    """
    items: list[T]
    total: int
    page: int
    size: int

    @property
    def total_pages(self) -> int:
        """
        总页数。
        """
        return max(1, -(-self.total // self.size))

    @property
    def has_next(self) -> bool:
        """
        是否有下一页。
        """
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """
        是否有上一页。
        """
        return self.page > 1


async def paginate(
    session: AsyncSession,
    model: type[T],
    user_id_attr: str = "user_id",
    user_id: object = None,
    page: int = 1,
    size: int = 20,
    order_attr: str = "create_at",
    descending: bool = True,
    extra_filter: object | None = None,
) -> PaginatedResult[T]:
    """
    通用数据库分页查询。
    参数:
        session: 数据库会话
        model: SQLModel 模型类
        user_id_attr: 用户 ID 字段名
        user_id: 用户 ID 值
        page: 页码（从 1 开始）
        size: 每页数量
        order_attr: 排序字段名
        descending: 是否降序
        extra_filter: 额外过滤条件
    返回:
        PaginatedResult 分页结果
    """
    query = select(model)
    if user_id is not None:
        query = query.where(getattr(model, user_id_attr) == user_id)
    if extra_filter is not None:
        query = query.where(extra_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.exec(count_query)).one()

    order_col = getattr(model, order_attr)
    query = query.order_by(order_col.desc() if descending else order_col.asc())
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await session.exec(query)
    items = list(result.all())

    return PaginatedResult(items=items, total=total, page=page, size=size)
```

- [ ] **Step 2: Commit**

```bash
git add src/utils/pagination.py
git commit -m "feat: 新增通用后端分页工具函数"
```

---

### Task 7: 后端 — 混合检索

**Files:**

- Create: `src/knowledge/search.py`

- [ ] **Step 1: 创建 search.py**

```python
from dataclasses import dataclass

from pymilvus import AnnSearchRequest, RRFRanker

from src.knowledge.embedding import embed_query
from src.knowledge.milvus import get_milvus_client, get_or_create_collection


@dataclass
class SearchHit:
    entry_id: str
    chunk_index: int
    text: str
    score: float


def hybrid_search(
    query: str,
    user_id: str,
    top_k: int = 5,
) -> list[SearchHit]:
    """
    混合检索：dense（GLM embedding-3）+ BM25 sparse，RRF 融合排序。
    参数:
        query: 查询文本
        user_id: 用户 ID
        top_k: 返回结果数量
    返回:
        SearchHit 列表
    """
    col_name = get_or_create_collection(user_id)
    client = get_milvus_client()

    dense_vector = embed_query(query)

    dense_req = AnnSearchRequest(
        data=[dense_vector],
        anns_field="dense_vector",
        param={"metric_type": "IP"},
        limit=top_k,
    )

    sparse_req = AnnSearchRequest(
        data=[query],
        anns_field="sparse_vector",
        param={"metric_type": "BM25"},
        limit=top_k,
    )

    results = client.hybrid_search(
        collection_name=col_name,
        reqs=[dense_req, sparse_req],
        ranker=RRFRanker(),
        limit=top_k,
        output_fields=["entry_id", "chunk_index", "text"],
    )

    hits: list[SearchHit] = []
    if results and results[0]:
        for hit in results[0]:
            hits.append(SearchHit(
                entry_id=hit["entity"]["entry_id"],
                chunk_index=hit["entity"]["chunk_index"],
                text=hit["entity"]["text"],
                score=hit["distance"],
            ))
    return hits
```

- [ ] **Step 2: Commit**

```bash
git add src/knowledge/search.py
git commit -m "feat: 新增知识库混合检索（dense + BM25 + RRF）"
```

---

### Task 8: 后端 — 知识库业务层

**Files:**

- Create: `src/knowledge/service.py`

- [ ] **Step 1: 创建 service.py**

```python
import os
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from src.knowledge.chunker import chunk_text, Chunk
from src.knowledge.embedding import aembed_texts
from src.knowledge.milvus import get_or_create_collection, get_milvus_client, delete_entry_chunks
from src.knowledge.search import hybrid_search, SearchHit
from src.service.db.db import KnowledgeEntry
from src.utils.pagination import PaginatedResult, paginate
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

    import uuid
    entry_id = str(uuid.uuid4())

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
    session.add(entry)
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
    return await paginate(
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
```

- [ ] **Step 2: Commit**

```bash
git add src/knowledge/service.py
git commit -m "feat: 新增知识库业务层（存入、删除、列表、检索）"
```

---

### Task 9: 后端 — 文件上传 Controller

**Files:**

- Create: `src/service/controller/FileUpload.py`

- [ ] **Step 1: 创建 FileUpload.py**

```python
import os
import uuid
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.db import FileUpload

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm", ".pdf", ".docx"}


def _ensure_upload_dir() -> None:
    """
    确保 uploads 目录存在。
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)


async def upload_file(
    session: AsyncSession,
    user_id: UUID,
    file_name: str,
    file_content: bytes,
) -> FileUpload:
    """
    上传文件到本地磁盘并写入数据库记录。
    参数:
        session: 数据库会话
        user_id: 用户 ID
        file_name: 原始文件名
        file_content: 文件二进制内容
    返回:
        FileUpload 数据库记录
    """
    _ensure_upload_dir()
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}")

    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    record = FileUpload(
        id=file_id,
        user_id=user_id,
        file_name=file_name,
        file_path=file_path,
        file_format=ext.lstrip("."),
        file_size=len(file_content),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_file_record(session: AsyncSession, file_id: str) -> FileUpload | None:
    """
    根据 ID 获取文件上传记录。
    参数:
        session: 数据库会话
        file_id: 文件 ID
    返回:
        FileUpload 记录或 None
    """
    return await session.get(FileUpload, file_id)


async def list_files(
    session: AsyncSession, user_id: UUID
) -> list[FileUpload]:
    """
    获取用户的文件上传列表。
    参数:
        session: 数据库会话
        user_id: 用户 ID
    返回:
        FileUpload 列表
    """
    result = await session.exec(
        select(FileUpload)
        .where(FileUpload.user_id == user_id)
        .order_by(FileUpload.create_at.desc())
    )
    return result.all()


async def delete_file(session: AsyncSession, file_id: str, user_id: UUID) -> bool:
    """
    删除文件（磁盘文件 + 数据库记录）。
    参数:
        session: 数据库会话
        file_id: 文件 ID
        user_id: 用户 ID
    返回:
        是否删除成功
    """
    record = await session.get(FileUpload, file_id)
    if not record or str(record.user_id) != str(user_id):
        return False
    if os.path.exists(record.file_path):
        os.remove(record.file_path)
    await session.delete(record)
    await session.commit()
    return True
```

- [ ] **Step 2: Commit**

```bash
git add src/service/controller/FileUpload.py
git commit -m "feat: 新增文件上传 Controller"
```

---

### Task 10: 后端 — 文件上传路由

**Files:**

- Create: `src/service/routes/upload.py`

- [ ] **Step 1: 创建 upload.py**

```python
import os

from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.auth.deps import CurrentUser
from src.service.controller.FileUpload import (
    upload_file,
    list_files,
    get_file_record,
    delete_file,
)
from src.service.db.database import get_session
from src.service.result import Result
from src.utils.reader import read

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/file")
async def upload_file_route(
    user: CurrentUser,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    上传文件到服务器。
    """
    content = await file.read()
    record = await upload_file(session, user.id, file.filename or "unknown.txt", content)
    return Result.success({
        "id": record.id,
        "file_name": record.file_name,
        "file_format": record.file_format,
        "file_size": record.file_size,
        "create_at": str(record.create_at),
    })


@router.get("/files")
async def list_files_route(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    获取当前用户的文件列表。
    """
    files = await list_files(session, user.id)
    return Result.success([
        {
            "id": f.id,
            "file_name": f.file_name,
            "file_format": f.file_format,
            "file_size": f.file_size,
            "create_at": str(f.create_at),
        }
        for f in files
    ])


@router.get("/files/{file_id}/content")
async def get_file_content_route(
    file_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    根据 file_id 获取文件文本内容。
    """
    record = await get_file_record(session, file_id)
    if not record or str(record.user_id) != str(user.id):
        return Result.error("文件不存在")
    try:
        text = read(record.file_path)
        return Result.success({"text": text})
    except Exception as e:
        return Result.error(f"文件读取失败: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file_route(
    file_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    删除文件。
    """
    success = await delete_file(session, file_id, user.id)
    if success:
        return Result.success(message="删除成功")
    return Result.error("文件不存在或无权删除")
```

- [ ] **Step 2: Commit**

```bash
git add src/service/routes/upload.py
git commit -m "feat: 新增文件上传路由"
```

---

### Task 11: 后端 — 知识库路由

**Files:**

- Create: `src/service/controller/KnowledgeEntry.py`
- Create: `src/service/routes/knowledge.py`

- [ ] **Step 1: 创建 KnowledgeEntry controller**

```python
from src.knowledge.service import (
    save_entry,
    delete_entry,
    list_entries,
    search_knowledge,
)
```

这是一个简单的 re-export，业务逻辑在 `src/knowledge/service.py` 中。

- [ ] **Step 2: 创建 knowledge.py 路由**

```python
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.auth.deps import CurrentUser
from src.service.db.database import get_session
from src.service.result import Result
from src.knowledge.service import (
    save_entry as _save_entry,
    delete_entry as _delete_entry,
    list_entries as _list_entries,
    search_knowledge as _search_knowledge,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class CreateEntryRequest(BaseModel):
    title: str
    content: Optional[str] = None
    file_id: Optional[str] = None
    source_type: str = "manual"
    source_id: Optional[str] = None


@router.post("/entries")
async def create_entry(
    body: CreateEntryRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    存入知识条目。
    """
    if not body.content and not body.file_id:
        return Result.error("content 和 file_id 至少提供一个")

    entry = await _save_entry(
        session=session,
        user_id=user.id,
        title=body.title,
        content=body.content,
        file_id=body.file_id,
        source_type=body.source_type,
        source_id=body.source_id,
    )
    return Result.success(entry)


@router.get("/entries")
async def get_entries(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    获取当前用户知识条目列表。
    """
    result = await _list_entries(session, user.id, page, size)
    return Result.success(result)


@router.get("/entries/{entry_id}")
async def get_entry_detail(
    entry_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    获取单个知识条目详情。
    """
    from src.service.db.db import KnowledgeEntry
    entry = await session.get(KnowledgeEntry, entry_id)
    if not entry or str(entry.user_id) != str(user.id):
        return Result.error("知识条目不存在")
    return Result.success(entry)


@router.delete("/entries/{entry_id}")
async def delete_entry_route(
    entry_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    删除知识条目。
    """
    success = await _delete_entry(session, user.id, entry_id)
    if success:
        return Result.success(message="删除成功")
    return Result.error("知识条目不存在或无权删除")


@router.post("/search")
async def search_route(
    body: dict,
    user: CurrentUser,
):
    """
    检索知识库。
    """
    query = body.get("query", "")
    top_k = body.get("top_k", 5)
    if not query:
        return Result.error("查询内容不能为空")
    hits = await _search_knowledge(user.id, query, top_k)
    return Result.success(hits)
```

- [ ] **Step 3: Commit**

```bash
git add src/service/controller/KnowledgeEntry.py src/service/routes/knowledge.py
git commit -m "feat: 新增知识库路由和 Controller"
```

---

### Task 12: 后端 — Chat Agent 工具（knowledge_search、read_file、save_to_knowledge）

**Files:**

- Create: `src/tools/knowledge_search.py`
- Create: `src/tools/read_file.py`
- Create: `src/tools/save_to_knowledge.py`

- [ ] **Step 1: 创建 knowledge_search.py**

```python
from langchain_community.tools import tool


@tool
async def knowledge_search(query: str) -> str:
    """
    知识库检索工具。当用户的问题可能命中已有知识库内容时调用。
    使用 dense + BM25 混合检索，返回最相关的知识片段。
    :query str: 检索查询文本
    """
    from src.knowledge.search import hybrid_search
    from src.utils.agent import get_current_user_id

    user_id = get_current_user_id()
    if not user_id:
        return "无法获取用户信息"

    hits = hybrid_search(query, user_id, top_k=5)
    if not hits:
        return "知识库中未找到相关内容"

    results = []
    for h in hits:
        results.append(f"[来源 chunk {h.chunk_index}] (相关度: {h.score:.4f})\n{h.text}")
    return "\n\n---\n\n".join(results)
```

- [ ] **Step 2: 创建 read_file.py**

```python
from langchain_community.tools import tool


@tool
async def read_file(file_id: str) -> str:
    """
    文件读取工具。根据 file_id 读取用户上传的文件内容。
    当用户在聊天中上传附件时，必须先调用此工具获取文件内容。
    :file_id str: 文件上传后返回的文件 ID
    """
    from src.service.db.database import engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from src.service.controller.FileUpload import get_file_record
    from src.utils.reader import read

    async with AsyncSession(engine) as session:
        record = await get_file_record(session, file_id)
        if not record:
            return f"未找到文件: {file_id}"
        try:
            text = read(record.file_path)
            return text
        except Exception as e:
            return f"文件读取失败: {str(e)}"
```

- [ ] **Step 3: 创建 save_to_knowledge.py**

```python
from langchain_community.tools import tool


@tool
async def save_to_knowledge(title: str, content: str) -> str:
    """
    将内容存入用户知识库。当用户明确要求存入知识库时调用。
    用户说"存入知识库"、"记录下来"、"保存到知识库"等类似意图时触发。
    :title str: 知识标题
    :content str: 要存入的完整内容
    """
    from src.service.db.database import engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from src.knowledge.service import save_entry
    from src.utils.agent import get_current_user_id

    user_id = get_current_user_id()
    if not user_id:
        return "无法获取用户信息，请先登录"

    from uuid import UUID
    async with AsyncSession(engine) as session:
        entry = await save_entry(
            session=session,
            user_id=UUID(user_id),
            title=title,
            content=content,
            source_type="manual",
        )
        return f"已成功存入知识库，标题: {entry.title}，共 {entry.chunk_count} 个分块"
```

- [ ] **Step 4: 在 src/utils/agent.py 中新增用户上下文管理（contextvars）**

在文件末尾追加：

```python
from contextvars import ContextVar

_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def set_current_user_id(user_id: str | None) -> None:
    """
    设置当前请求的用户 ID（协程安全）。
    基于 contextvars 实现，每个异步请求有独立的上下文。
    """
    _current_user_id.set(user_id)


def get_current_user_id() -> str | None:
    """
    获取当前请求的用户 ID。
    """
    return _current_user_id.get()
```

- [ ] **Step 5: Commit**

```bash
git add src/tools/knowledge_search.py src/tools/read_file.py src/tools/save_to_knowledge.py src/utils/agent.py
git commit -m "feat: 新增 Chat Agent 知识库检索、文件读取、存入知识库工具"
```

---

### Task 13: 后端 — ChatState、系统提示词、工具绑定、路由集成

**Files:**

- Modify: `src/agent/chat/config.py`
- Modify: `src/agent/chat/create_agent.py`
- Modify: `src/agent/chat/nodes/chat.py`
- Modify: `src/service/routes/chat.py`
- Modify: `src/service/__init__.py`

- [ ] **Step 1: 修改 ChatState — 新增 file_ids**

在 `src/agent/chat/config.py` 的 ChatState 中新增字段：

```python
class ChatState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str
    research_result: Optional[str]
    research_active: bool
    file_ids: Optional[list[str]]
```

同步更新 `get_initial_chat_state` 函数，添加：

```python
"file_ids": state.get("file_ids", None),
```

- [ ] **Step 2: 修改 create_agent.py — 扩展工具列表**

修改 `src/agent/chat/create_agent.py`：

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.func import END, START
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent.chat.config import ChatState
from src.agent.chat.nodes.chat import chat_node
from src.tools.research import research
from src.tools.knowledge_search import knowledge_search
from src.tools.read_file import read_file
from src.tools.save_to_knowledge import save_to_knowledge


def _build_chat_graph(checkpointer: AsyncPostgresSaver):
    builder = StateGraph(ChatState)
    builder.add_node("chat", chat_node)
    builder.add_node("tools", ToolNode([research, knowledge_search, read_file, save_to_knowledge]))

    builder.add_edge(START, "chat")
    builder.add_edge("tools", "chat")

    builder.add_conditional_edges(
        "chat",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )

    graph = builder.compile(checkpointer=checkpointer)

    return graph


def create_chat_agent(checkpointer: AsyncPostgresSaver):
    return _build_chat_graph(checkpointer=checkpointer)
```

- [ ] **Step 3: 修改 chat.py — 更新系统提示词和工具绑定**

替换 `src/agent/chat/nodes/chat.py` 中 `CHAT_SYSTEM_PROMPT`：

```python
CHAT_SYSTEM_PROMPT = """你是一个知识助手。你可以：
1. 直接回答用户的简单问题（闲聊、解释概念、提供建议）
2. 调用 knowledge_search 检索已有知识库
3. 当用户需要深度研究时，调用 research 工具
4. 调用 read_file 读取用户上传的附件内容
5. 调用 save_to_knowledge 将内容存入知识库

规则：
- 用户消息附带附件时，必须先调用 read_file 获取文件内容，然后根据用户意图处理
- 根据用户意图决定是否调用 save_to_knowledge
- 用户说"存入知识库"、"记录下来"、"保存一下"等类似意图时，调用 save_to_knowledge
- 对于非简单问题，优先调用 knowledge_search 查看是否有相关知识
- knowledge_search 有结果时，结合检索结果回答，无需再 research
- knowledge_search 无结果且需要深度研究时，再调用 research
- 触发 research 的场景：用户要求总结、分析、深度研究某个话题；用户消息以 /research 开头；需要搜索多个来源并综合分析

回复使用中文。"""
```

修改 `chat_node` 函数中的工具绑定和 messages 注入：

```python
from langchain.messages import SystemMessage, HumanMessage
from src.agent.chat.config import ChatState
from src.llm import init_model
from src.tools.research import research
from src.tools.knowledge_search import knowledge_search
from src.tools.read_file import read_file
from src.tools.save_to_knowledge import save_to_knowledge

CHAT_SYSTEM_PROMPT = """你是一个知识助手。你可以：
1. 直接回答用户的简单问题（闲聊、解释概念、提供建议）
2. 调用 knowledge_search 检索已有知识库
3. 当用户需要深度研究时，调用 research 工具
4. 调用 read_file 读取用户上传的附件内容
5. 调用 save_to_knowledge 将内容存入知识库

规则：
- 用户消息附带附件时，必须先调用 read_file 获取文件内容，然后根据用户意图处理
- 根据用户意图决定是否调用 save_to_knowledge
- 用户说"存入知识库"、"记录下来"、"保存一下"等类似意图时，调用 save_to_knowledge
- 对于非简单问题，优先调用 knowledge_search 查看是否有相关知识
- knowledge_search 有结果时，结合检索结果回答，无需再 research
- knowledge_search 无结果且需要深度研究时，再调用 research
- 触发 research 的场景：用户要求总结、分析、深度研究某个话题；用户消息以 /research 开头；需要搜索多个来源并综合分析

回复使用中文。"""


async def chat_node(state: ChatState) -> dict:
    llm = init_model()
    llm_with_tools = llm.bind_tools([research, knowledge_search, read_file, save_to_knowledge])

    state_messages = state.get("messages", [])
    existing_messages = []

    for msg in state_messages:
        if isinstance(msg, SystemMessage):
            continue
        existing_messages.append(msg)

    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)] + existing_messages

    file_ids = state.get("file_ids")
    if file_ids:
        ids_text = ", ".join(file_ids)
        messages.append(HumanMessage(content=f"[系统提示：用户上传了附件，file_id 为 {ids_text}，请调用 read_file 工具获取内容后处理用户请求]"))

    response = await llm_with_tools.ainvoke(messages)
    return {
        "messages": [response],
    }
```

关键点：当 `file_ids` 非空时，在 messages 末尾追加一条 HumanMessage 告知 LLM 有附件，LLM 据此决定调用 `read_file`。这条消息不会持久化到数据库（它是临时注入的，不经过 PG）。

- [ ] **Step 4: 修改 ChatStart — 新增 file_ids**

在 `src/service/routes/chat.py` 的 ChatStart 模型中新增：

```python
class ChatStart(BaseModel):
    query: str
    thread_id: Optional[str] = None
    file_ids: Optional[list[str]] = None
```

在 `chat_start` 函数中，构造 state 时传入 file_ids：

```python
state = {"user_query": body.query, "file_ids": body.file_ids}
```

找到 `state = {"user_query": body.query}` 那行，替换为上面的版本。

- [ ] **Step 5: 修改 `src/service/__init__.py` — 注册新路由、初始化 Milvus**

在 import 区域新增：

```python
from src.service.routes.knowledge import router as knowledge_router
from src.service.routes.upload import router as upload_router
```

在 `lifespan` 函数中，`yield` 之前新增：

```python
    from src.knowledge.milvus import get_milvus_client
    get_milvus_client()
    app.state.milvus_client = True

    import os
    os.makedirs(os.getenv("UPLOAD_DIR", "./uploads"), exist_ok=True)
```

在 `create_agent_service` 函数中新增路由注册：

```python
    app.include_router(knowledge_router)
    app.include_router(upload_router)
```

- [ ] **Step 6: Commit**

```bash
git add src/agent/chat/config.py src/agent/chat/create_agent.py src/agent/chat/nodes/chat.py src/service/routes/chat.py src/service/__init__.py
git commit -m "feat: Chat Agent 集成知识库检索、文件读取、存入知识库工具"
```

---

### Task 14: 前端 — 类型定义和 API 客户端

**Files:**

- Create: `frontend/src/types/knowledge.ts`
- Create: `frontend/src/api/uploadApi.ts`
- Create: `frontend/src/api/knowledgeApi.ts`
- Modify: `frontend/src/types/agent.ts`

- [ ] **Step 1: 创建 `frontend/src/types/knowledge.ts`**

```typescript
export interface KnowledgeEntry {
  id: string;
  user_id: string;
  title: string;
  source_type: "research" | "manual" | "file";
  source_id?: string;
  chunk_count: number;
  content_preview?: string;
  create_at: string;
}

export interface KnowledgeEntryListResult {
  items: KnowledgeEntry[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface FileUploadRecord {
  id: string;
  file_name: string;
  file_format: string;
  file_size: number;
  create_at: string;
}

export interface SearchResult {
  entry_id: string;
  chunk_index: number;
  text: string;
  score: number;
}
```

- [ ] **Step 2: 创建 `frontend/src/api/uploadApi.ts`**

```typescript
import { httpClient } from "./client";
import type { FileUploadRecord } from "../types/knowledge";

export const uploadApi = {
  async uploadFile(file: File): Promise<FileUploadRecord> {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await httpClient.post<FileUploadRecord>("/upload/file", formData);
    return data;
  },

  async getFiles(): Promise<FileUploadRecord[]> {
    const { data } = await httpClient.get<FileUploadRecord[]>("/upload/files");
    return data;
  },

  async getFileContent(fileId: string): Promise<string> {
    const { data } = await httpClient.get<{ text: string }>(`/upload/files/${fileId}/content`);
    return data.text;
  },

  async deleteFile(fileId: string): Promise<void> {
    await httpClient.delete(`/upload/files/${fileId}`);
  },
};
```

- [ ] **Step 3: 创建 `frontend/src/api/knowledgeApi.ts`**

```typescript
import { httpClient } from "./client";
import type { KnowledgeEntry, KnowledgeEntryListResult, SearchResult } from "../types/knowledge";

export const knowledgeApi = {
  async createEntry(params: {
    title: string;
    content?: string;
    file_id?: string;
    source_type?: string;
    source_id?: string;
  }): Promise<KnowledgeEntry> {
    const { data } = await httpClient.post<KnowledgeEntry>("/knowledge/entries", params);
    return data;
  },

  async getEntries(page = 1, size = 20): Promise<KnowledgeEntryListResult> {
    const { data } = await httpClient.get<KnowledgeEntryListResult>("/knowledge/entries", { page, size });
    return data;
  },

  async getEntry(entryId: string): Promise<KnowledgeEntry> {
    const { data } = await httpClient.get<KnowledgeEntry>(`/knowledge/entries/${entryId}`);
    return data;
  },

  async deleteEntry(entryId: string): Promise<void> {
    await httpClient.delete(`/knowledge/entries/${entryId}`);
  },

  async search(query: string, topK = 5): Promise<SearchResult[]> {
    const { data } = await httpClient.post<SearchResult[]>("/knowledge/search", { query, top_k: topK });
    return data;
  },
};
```

- [ ] **Step 4: 修改 `frontend/src/types/agent.ts` — SubmitRequest 新增 file_ids**

```typescript
export interface SubmitRequest {
  query: string;
  thread_id?: string;
  file_ids?: string[];
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/knowledge.ts frontend/src/api/uploadApi.ts frontend/src/api/knowledgeApi.ts frontend/src/types/agent.ts
git commit -m "feat: 前端新增知识库类型定义和 API 客户端"
```

---

### Task 15: 前端 — 通用 UI 组件（Modal、FileUploader、Pagination）

**Files:**

- Create: `frontend/src/components/Modal.tsx`
- Create: `frontend/src/components/FileUploader.tsx`

- [ ] **Step 1: 创建 `frontend/src/components/Modal.tsx`**

通用 Modal 壳组件，遵循项目 Tailwind CSS v4 玻璃态风格：

```tsx
import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from "@headlessui/react";
import { X } from "lucide-react";
import type { ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}

export default function Modal({ open, onClose, title, children, footer }: ModalProps) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <DialogBackdrop className="fixed inset-0 bg-black/40" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="glass-card w-full max-w-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-base font-semibold text-ink-100">{title}</DialogTitle>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-ink-400 hover:text-ink-100 hover:bg-white/40 transition-all cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="mb-4">{children}</div>
          {footer && <div className="flex justify-end gap-2">{footer}</div>}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
```

- [ ] **Step 2: 创建 `frontend/src/components/FileUploader.tsx`**

通用文件上传组件，支持拖拽和点击上传，显示文件列表：

```tsx
import { useCallback, useRef, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import type { FileUploadRecord } from "../types/knowledge";
import { uploadApi } from "../api/uploadApi";

interface FileUploaderProps {
  onUploaded: (file: FileUploadRecord) => void;
  accept?: string;
  multiple?: boolean;
}

const ACCEPTED = ".txt,.md,.markdown,.html,.htm,.pdf,.docx";

export default function FileUploader({ onUploaded, accept = ACCEPTED, multiple = false }: FileUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;
      setError(null);
      setUploading(true);
      try {
        for (let i = 0; i < files.length; i++) {
          const record = await uploadApi.uploadFile(files[i]);
          onUploaded(record);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "上传失败");
      } finally {
        setUploading(false);
      }
    },
    [onUploaded],
  );

  return (
    <div>
      <div
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
          dragOver ? "border-accent bg-accent-bg/20" : "border-ink-400/30 hover:border-ink-400/60"
        }`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
      >
        <Upload className="w-6 h-6 mx-auto mb-2 text-ink-400" />
        <p className="text-sm text-ink-400">
          {uploading ? "上传中..." : "点击或拖拽文件到此处"}
        </p>
        <p className="text-xs text-ink-400/60 mt-1">支持 txt、md、html、pdf、docx</p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 3: 创建 `frontend/src/hooks/usePagination.ts`**

通用分页 hook，封装分页状态和数据加载：

```typescript
import { useState, useCallback } from "react";

export interface PaginationState {
  page: number;
  size: number;
  total: number;
  total_pages: number;
}

export function usePagination(initialSize = 20) {
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    size: initialSize,
    total: 0,
    total_pages: 0,
  });

  const setPage = useCallback((page: number) => {
    setPagination((prev) => ({ ...prev, page }));
  }, []);

  const updateFromResponse = useCallback((data: { total: number; page: number; size: number; total_pages: number }) => {
    setPagination({
      page: data.page,
      size: data.size,
      total: data.total,
      total_pages: data.total_pages,
    });
  }, []);

  return { pagination, setPage, updateFromResponse };
}
```

- [ ] **Step 4: 创建 `frontend/src/components/Pagination.tsx`**

通用分页 UI 组件，基于 Headless UI 无障碍理念：

```tsx
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { PaginationState } from "../hooks/usePagination";

interface PaginationProps {
  pagination: PaginationState;
  onPageChange: (page: number) => void;
}

export default function Pagination({ pagination, onPageChange }: PaginationProps) {
  const { page, total_pages } = pagination;

  if (total_pages <= 1) return null;

  const pages: (number | "...")[] = [];
  if (total_pages <= 7) {
    for (let i = 1; i <= total_pages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("...");
    for (let i = Math.max(2, page - 1); i <= Math.min(total_pages - 1, page + 1); i++) {
      pages.push(i);
    }
    if (page < total_pages - 2) pages.push("...");
    pages.push(total_pages);
  }

  return (
    <div className="flex items-center justify-center gap-1">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="w-8 h-8 rounded-lg flex items-center justify-center text-ink-400 hover:bg-white/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      {pages.map((p, i) =>
        p === "..." ? (
          <span key={`dots-${i}`} className="w-8 h-8 flex items-center justify-center text-xs text-ink-400">
            ...
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm transition-colors cursor-pointer ${
              page === p ? "bg-accent text-white" : "text-ink-400 hover:bg-white/30"
            }`}
          >
            {p}
          </button>
        ),
      )}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= total_pages}
        className="w-8 h-8 rounded-lg flex items-center justify-center text-ink-400 hover:bg-white/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Modal.tsx frontend/src/components/FileUploader.tsx frontend/src/hooks/usePagination.ts frontend/src/components/Pagination.tsx
git commit -m "feat: 前端新增通用 Modal（Headless UI）、FileUploader、Pagination 组件"
```

---

### Task 16: 前端 — 知识库管理页面

**Files:**

- Create: `frontend/src/pages/knowledge/KnowledgePage.tsx`
- Create: `frontend/src/pages/knowledge/AddKnowledgeModal.tsx`
- Modify: `frontend/src/routes/index.tsx`
- Modify: `frontend/src/components/SessionSidebar.tsx`

- [ ] **Step 1: 创建 `frontend/src/pages/knowledge/AddKnowledgeModal.tsx`**

新增知识业务弹窗，组合 Modal + FileUploader + Headless UI Tab：

```tsx
import { useState } from "react";
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from "@headlessui/react";
import { FileText, X } from "lucide-react";
import Modal from "../../components/Modal";
import FileUploader from "../../components/FileUploader";
import type { FileUploadRecord } from "../../types/knowledge";
import { knowledgeApi } from "../../api/knowledgeApi";

interface AddKnowledgeModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  initialContent?: string;
  initialTitle?: string;
}

export default function AddKnowledgeModal({ open, onClose, onSaved, initialContent, initialTitle }: AddKnowledgeModalProps) {
  const [title, setTitle] = useState(initialTitle || "");
  const [content, setContent] = useState(initialContent || "");
  const [fileId, setFileId] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<FileUploadRecord | null>(null);
  const [tab, setTab] = useState<"text" | "file">("text");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async () => {
    if (!title) return;
    if (tab === "text" && !content) return;
    if (tab === "file" && !fileId) return;
    setSaving(true);
    try {
      await knowledgeApi.createEntry({
        title,
        content: tab === "text" ? content : undefined,
        file_id: tab === "file" ? fileId! : undefined,
        source_type: tab === "file" ? "file" : "manual",
      });
      onSaved();
      onClose();
      setTitle("");
      setContent("");
      setFileId(null);
      setUploadedFile(null);
    } catch {
    } finally {
      setSaving(false);
    }
  };

  const handleFileUploaded = (record: FileUploadRecord) => {
    setFileId(record.id);
    setUploadedFile(record);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="新增知识"
      footer={
        <>
          <button onClick={onClose} className="px-4 py-1.5 text-sm text-ink-400 hover:text-ink-100 transition-colors cursor-pointer">
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving || !title || (tab === "text" ? !content : !fileId)}
            className="px-4 py-1.5 text-sm rounded-lg bg-accent text-white hover:opacity-90 disabled:opacity-50 transition-all cursor-pointer"
          >
            {saving ? "保存中..." : "保存"}
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <label className="text-xs text-ink-400 mb-1 block">标题</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-white/40 border border-white/30 text-sm text-ink-100 focus:outline-none focus:border-accent"
            placeholder="输入知识标题"
          />
        </div>
        <div>
          <TabGroup onChange={(idx) => setTab(idx === 0 ? "text" : "file")}>
            <TabList className="flex gap-2 mb-2">
              {(["text", "file"] as const).map((t) => (
                <Tab
                  key={t}
                  className="px-3 py-1 text-xs rounded-lg transition-colors cursor-pointer data-[selected]:bg-accent data-[selected]:text-white data-[not-selected]:bg-white/30 data-[not-selected]:text-ink-400"
                >
                  {t === "text" ? "手动输入" : "文件上传"}
                </Tab>
              ))}
            </TabList>
            <TabPanels>
              <TabPanel>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full h-40 px-3 py-2 rounded-lg bg-white/40 border border-white/30 text-sm text-ink-100 focus:outline-none focus:border-accent resize-none"
                  placeholder="粘贴或输入知识内容"
                />
              </TabPanel>
              <TabPanel>
                {uploadedFile ? (
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/30">
                    <FileText className="w-4 h-4 text-accent" />
                    <span className="text-sm text-ink-100 flex-1 truncate">{uploadedFile.file_name}</span>
                    <button
                      onClick={() => { setFileId(null); setUploadedFile(null); }}
                      className="text-ink-400 hover:text-red-500 cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ) : (
                  <FileUploader onUploaded={handleFileUploaded} />
                )}
              </TabPanel>
            </TabPanels>
          </TabGroup>
        </div>
      </div>
    </Modal>
  );
}
```

需要在顶部 import `FileText` 和 `X` from `lucide-react`。

- [ ] **Step 2: 创建 `frontend/src/pages/knowledge/KnowledgePage.tsx`**

```tsx
import { useState, useEffect, useCallback } from "react";
import { Trash2, Plus, Search, FileText, MessageSquare, BookOpen } from "lucide-react";
import type { KnowledgeEntry } from "../../types/knowledge";
import { knowledgeApi } from "../../api/knowledgeApi";
import { usePagination } from "../../hooks/usePagination";
import Pagination from "../../components/Pagination";
import AddKnowledgeModal from "./AddKnowledgeModal";

const SOURCE_LABELS: Record<string, { label: string; icon: typeof FileText; color: string }> = {
  research: { label: "研究", icon: BookOpen, color: "bg-green-50 text-green-600" },
  manual: { label: "手动", icon: MessageSquare, color: "bg-blue-50 text-blue-600" },
  file: { label: "文件", icon: FileText, color: "bg-purple-50 text-purple-600" },
};

export default function KnowledgePage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<{ text: string; score: number }[] | null>(null);
  const { pagination, setPage, updateFromResponse } = usePagination();

  const loadEntries = useCallback(async () => {
    try {
      const result = await knowledgeApi.getEntries(pagination.page, pagination.size);
      setEntries(result.items);
      updateFromResponse(result);
    } catch {}
  }, [pagination.page, pagination.size, updateFromResponse]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleDelete = async (id: string) => {
    if (!confirm("确认删除此知识条目？")) return;
    try {
      await knowledgeApi.deleteEntry(id);
      loadEntries();
    } catch {}
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    try {
      const results = await knowledgeApi.search(searchQuery);
      setSearchResults(results);
    } catch {}
  };

  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-semibold text-ink-100">知识库管理</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-white text-sm hover:opacity-90 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          新增知识
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 px-3 py-2 rounded-lg bg-white/40 border border-white/30 text-sm text-ink-100 focus:outline-none focus:border-accent"
          placeholder="搜索知识库..."
        />
        <button onClick={handleSearch} className="px-3 py-2 rounded-lg bg-white/30 hover:bg-white/50 transition-colors cursor-pointer">
          <Search className="w-4 h-4 text-ink-400" />
        </button>
      </div>

      {searchResults !== null && (
        <div className="glass-card p-4 mb-4">
          <h3 className="text-sm font-medium text-ink-100 mb-2">搜索结果</h3>
          {searchResults.length === 0 ? (
            <p className="text-xs text-ink-400">未找到相关内容</p>
          ) : (
            <div className="space-y-2">
              {searchResults.map((r, i) => (
                <div key={i} className="p-3 rounded-lg bg-white/30">
                  <p className="text-xs text-ink-400 mb-1">相关度: {r.score.toFixed(4)}</p>
                  <p className="text-sm text-ink-100 whitespace-pre-wrap">{r.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        {entries.map((entry) => {
          const src = SOURCE_LABELS[entry.source_type] || SOURCE_LABELS.manual;
          const Icon = src.icon;
          return (
            <div key={entry.id} className="glass-card p-4 flex items-start gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${src.color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-ink-100 truncate">{entry.title}</h3>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${src.color}`}>{src.label}</span>
                </div>
                {entry.content_preview && (
                  <p className="text-xs text-ink-400 mt-1 line-clamp-2">{entry.content_preview}</p>
                )}
                <div className="flex items-center gap-3 mt-1.5 text-[11px] text-ink-400">
                  <span>{entry.chunk_count} 个分块</span>
                  <span>{new Date(entry.create_at).toLocaleString("zh-CN")}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(entry.id)}
                className="text-ink-400 hover:text-red-500 transition-colors cursor-pointer mt-1"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        })}
        {entries.length === 0 && (
          <div className="text-center py-12 text-ink-400">
            <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm">暂无知识条目</p>
          </div>
        )}
      </div>

      <Pagination pagination={pagination} onPageChange={setPage} />

      <AddKnowledgeModal open={showAdd} onClose={() => setShowAdd(false)} onSaved={loadEntries} />
    </div>
  );
}
```

- [ ] **Step 3: 修改路由 — 新增 /knowledge**

在 `frontend/src/routes/index.tsx` 中：

添加 import：

```typescript
import KnowledgePage from "../pages/knowledge/KnowledgePage";
```

在 ProtectedRoute → AppLayout 的 children 数组中新增：

```typescript
children: [
  { path: "/", element: <ChatPage /> },
  { path: "/knowledge", element: <KnowledgePage /> },
],
```

- [ ] **Step 4: 修改 SessionSidebar — 新增知识库导航**

在 `frontend/src/components/SessionSidebar.tsx` 中：

添加 import：

```typescript
import { Link } from "react-router-dom";
import { Database } from "lucide-react";
```

在侧栏底部用户信息区域之前（`<div className="px-3 py-3 border-t...">` 之前），新增：

```tsx
<div className="px-3 py-2 border-t border-white/30">
  <Link
    to="/knowledge"
    className="flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm text-ink-400 hover:text-ink-100 hover:bg-white/30 transition-all"
  >
    <Database className="w-4 h-4" />
    知识库
  </Link>
</div>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/knowledge/ frontend/src/routes/index.tsx frontend/src/components/SessionSidebar.tsx
git commit -m "feat: 前端新增知识库管理页面和导航入口"
```

---

### Task 17: 前端 — Chat 页面集成（附件上传 + 存入知识库按钮）

**Files:**

- Modify: `frontend/src/pages/chat/ChatPage.tsx`
- Modify: `frontend/src/components/ResultCard.tsx`
- Modify: `frontend/src/hooks/useAgentChat.ts`
- Modify: `frontend/src/api/agentApi.ts`

- [ ] **Step 1: 修改 useAgentChat — submit 支持 file_ids**

在 `frontend/src/hooks/useAgentChat.ts` 中修改 `submit` 函数签名：

```typescript
const submit = useCallback(
  async (query: string, fileIds?: string[]) => {
```

修改 `submitSSETask` 调用，传入 file_ids：

```typescript
await agentApi.submitSSETask(
  { query, thread_id: activeThreadId ?? undefined, file_ids: fileIds },
  { ... },
);
```

在 return 中添加 `fileIds` 相关状态管理（pendingFileIds 等，在 ChatPage 中管理即可，此处只需支持参数传递）。

- [ ] **Step 2: 修改 ChatPage — 搜索框新增附件上传**

在 `frontend/src/pages/chat/ChatPage.tsx` 中：

添加 import：

```typescript
import { Paperclip, X } from "lucide-react";
import { uploadApi } from "../../api/uploadApi";
import type { FileUploadRecord } from "../../types/knowledge";
```

在 ChatPage 组件中新增附件状态：

```typescript
const [pendingFiles, setPendingFiles] = useState<FileUploadRecord[]>([]);
```

在 SearchForm 区域之前添加附件上传按钮和已上传文件标签。在 submit 调用时传入 file_ids：

```typescript
submit(query, pendingFiles.map((f) => f.id));
setPendingFiles([]);
```

上传按钮：点击触发隐藏 input[type=file]，上传完成后显示文件名 + 删除按钮。

- [ ] **Step 3: 修改 ResultCard — 新增"存入知识库"按钮**

在 `frontend/src/components/ResultCard.tsx` 中：

添加 props：

```typescript
interface ResultCardProps {
  state: AgentState;
  onSaveToKnowledge?: (content: string) => void;
}
```

在卡片底部（confidence 之后）新增按钮：

```tsx
{onSaveToKnowledge && (
  <button
    onClick={() => onSaveToKnowledge(state.final_answer)}
    className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-accent bg-accent-bg hover:opacity-80 transition-all cursor-pointer"
  >
    <Plus className="w-3.5 h-3.5" />
    存入知识库
  </button>
)}
```

添加 import `Plus` from `lucide-react`。

- [ ] **Step 4: 修改 ChatPage — 处理存入知识库**

在 ChatPage 中添加存入知识库的处理逻辑：点击按钮后弹出 AddKnowledgeModal，预填 content 和 title。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/chat/ChatPage.tsx frontend/src/components/ResultCard.tsx frontend/src/hooks/useAgentChat.ts frontend/src/api/agentApi.ts
git commit -m "feat: 前端 Chat 页面集成附件上传和存入知识库按钮"
```

---

### Task 18: 后端 — SSE 流中传递 file_ids 到 ChatState

**Files:**

- Modify: `src/service/routes/chat.py`
- Modify: `src/service/routes/sse.py`

- [ ] **Step 1: 修改 chat_start — 将 file_ids 注入 state**

在 `src/service/routes/chat.py` 的 `chat_start` 函数中，构造 initial_state 前注入 file_ids：

```python
state["file_ids"] = body.file_ids
```

在 `initial_state = get_initial_state(state)` 之前添加。

- [ ] **Step 2: 修改 sse.py — 传递 file_ids 到 agent config 或 state**

如果 file_ids 存在，需要在 Agent 调用前将其设为可用。在 `event_generator` 中，将 file_ids 信息传入 initial_state。

这里需要确保 `from src.utils.agent import set_current_user_id` 在 chat_start 中被调用，以便 Agent 工具能获取 user_id：

在 `chat_start` 函数中，获取 user 后：

```python
from src.utils.agent import set_current_user_id
set_current_user_id(str(user.id))
```

- [ ] **Step 3: Commit**

```bash
git add src/service/routes/chat.py src/service/routes/sse.py
git commit -m "feat: 聊天路由支持 file_ids 传递和用户上下文注入"
```

---

### Task 19: 记忆文件更新

**Files:**

- Modify: `.opencode/memory/backend.md`
- Modify: `.opencode/memory/agent.md`
- Modify: `.opencode/memory/frontend.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: 更新 backend.md**

在目录结构中新增 `knowledge/` 模块、`FileUpload` controller、`KnowledgeEntry` controller、`upload.py` 路由、`knowledge.py` 路由的描述。在路由总览中新增 `/upload/*` 和 `/knowledge/*` 路由表格。在数据库模型中新增 `FileUpload` 和 `KnowledgeEntry` 表描述。

- [ ] **Step 2: 更新 agent.md**

在 Chat Agent 工具列表中新增 `knowledge_search`、`read_file`、`save_to_knowledge`。更新系统提示词说明。新增 ChatState 的 `file_ids` 字段。

- [ ] **Step 3: 更新 frontend.md**

在路由表中新增 `/knowledge` 路由。在目录结构中新增 `pages/knowledge/`、新增组件。在核心 Hooks 中更新 `submit` 签名。

- [ ] **Step 4: 更新 AGENTS.md**

在环境变量部分新增 `MILVUS_URI`、`ZHIPU_API_KEY`、`UPLOAD_DIR`。

- [ ] **Step 5: Commit**

```bash
git add .opencode/memory/backend.md .opencode/memory/agent.md .opencode/memory/frontend.md AGENTS.md
git commit -m "docs: 更新记忆文件，补充知识库功能描述"
```

---

## Self-Review Checklist

### Spec Coverage

| 需求                     | 对应 Task                                                           |
| ------------------------ | ------------------------------------------------------------------- |
| 用户独立知识库           | Task 5（collection per user）                                       |
| 三种存入触发             | Task 8（service.save_entry）、Task 11（路由）、Task 17（前端）      |
| Chat 页面附件上传        | Task 9-10（上传 API）、Task 17（前端集成）                          |
| 知识库管理页面           | Task 15-16                                                          |
| Milvus + GLM embedding-3 | Task 3、Task 5                                                      |
| BM25 混合检索            | Task 7                                                              |
| Chat Agent 自动检索      | Task 12-13                                                          |
| 文件解析复用 reader.py   | Task 9（直接调用 read()）                                           |
| Headless UI 通用组件     | Task 15（Modal、Pagination、FileUploader）                          |
| 通用分页（前后端复用）   | Task 6（后端 paginate）、Task 15（前端 usePagination + Pagination） |

### Placeholder Scan

无 TBD、TODO、"implement later"。

### Type Consistency

- KnowledgeEntry 的 id 在 PG 中为 str（UUID），在 Milvus 中为 VARCHAR entry_id —— 一致
- ChatState.file_ids 为 `Optional[list[str]]` —— 前后端一致
- SubmitRequest.file_ids 为 `string[] | undefined` —— 前后端一致
- PaginatedResult 后端返回 `total_pages` —— 前端 `PaginationState.total_pages` 一致
- 后端 paginate 返回 `PaginatedResult[T]`，路由层序列化为 `{items, total, page, size, total_pages}` —— 前端 `KnowledgeEntryListResult` 一致
