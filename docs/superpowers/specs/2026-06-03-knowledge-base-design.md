# 知识库功能设计文档

## 概述

为问答系统接入用户独立知识库，支持 research 结果存入、文件上传存入、手动文本存入三种方式，使用 Milvus 向量库 + GLM embedding-3 + BM25 混合检索，Chat Agent 自动检索知识库辅助回答。

## 需求摘要

- 用户独立知识库（互不干扰）
- 三种存入触发：research 结束后、Chat 中用户主动要求、知识库管理页面上传文件
- Chat 页面支持上传附件，Agent 读取内容后判断是否存入知识库
- 文件上传为独立服务，与知识库解耦
- 知识库管理页面：查看、搜索、删除
- 检索方式：dense（GLM embedding-3）+ BM25 sparse 混合检索，RRF 融合排序
- 文件解析复用已有 `src/utils/reader.py`（支持 txt/md/html/pdf/docx）

## 整体架构

### 新增模块

```
src/
├── knowledge/                    # 知识库核心模块
│   ├── __init__.py
│   ├── milvus.py                 # Milvus 连接管理、Collection 初始化
│   ├── embedding.py              # GLM embedding-3 封装
│   ├── chunker.py                # 文本分块逻辑
│   ├── service.py                # 知识库 CRUD 业务逻辑
│   └── search.py                 # 混合检索（dense + BM25 + RRF）
├── service/
│   ├── controller/
│   │   ├── KnowledgeEntry.py     # 知识条目 CRUD
│   │   └── FileUpload.py         # 文件上传管理
│   ├── db/
│   │   └── db.py                 # 新增 KBEntry、FileUpload 表
│   └── routes/
│       ├── knowledge.py          # /knowledge/* 路由
│       └── upload.py             # /upload/* 路由
├── tools/
│   ├── knowledge_search.py       # Chat Agent 知识库检索工具
│   ├── read_file.py              # Chat Agent 文件读取工具
│   └── save_to_knowledge.py      # Chat Agent 存入知识库工具
└── agent/chat/
    ├── config.py                 # ChatState 新增 file_ids 字段
    ├── create_agent.py           # 工具列表扩展
    └── nodes/chat.py             # 系统提示词更新
```

## 数据模型

### PostgreSQL 新增表

#### file_upload

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 文件 ID |
| user_id | UUID (FK → fullauth_users.id) | 所属用户 |
| file_name | str | 原始文件名 |
| file_path | str | 磁盘存储路径 |
| file_format | str | 文件格式（txt/md/pdf/docx/html） |
| file_size | int | 文件大小（字节） |
| create_at | datetime | 上传时间 |

#### knowledge_entry

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | 条目 ID |
| user_id | UUID (FK → fullauth_users.id) | 所属用户 |
| title | str | 知识标题 |
| source_type | str | 来源类型：research / manual / file |
| source_id | UUID (nullable) | 关联来源 ID（file_upload.id 或 chat 会话 ID） |
| chunk_count | int | 分块数量 |
| content_preview | str | 内容预览（前 200 字） |
| create_at | datetime | 创建时间 |

### Milvus Collection

Collection 名：`knowledge_{user_id}`（每个用户独立 collection）

| 字段 | 类型 | 说明 |
|------|------|------|
| pk | VARCHAR (PK, auto_id) | 主键 |
| entry_id | VARCHAR | 关联 knowledge_entry.id |
| chunk_index | INT32 | 分块序号 |
| text | VARCHAR (enable_analyzer=True) | 原始文本（BM25 输入源） |
| dense_vector | FLOAT_VECTOR(dim=2048) | GLM embedding-3 dense 向量 |
| sparse_vector | SPARSE_FLOAT_VECTOR | BM25 自动生成的 sparse 向量 |

索引：
- dense_vector → AUTOINDEX, metric=IP
- sparse_vector → SPARSE_INVERTED_INDEX, metric=BM25, params={"inverted_index_algo": "DAAT_MAXSCORE"}

BM25 Function：input=["text"] → output=["sparse_vector"]

## API 设计

### 文件上传 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /upload/file | 上传文件（multipart/form-data），返回 file_id 等 |
| GET | /upload/files | 获取当前用户的文件列表 |
| GET | /upload/files/{id}/content | 根据 file_id 获取文件文本内容 |
| DELETE | /upload/files/{id} | 删除文件（磁盘 + PG 记录） |

### 知识库 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /knowledge/entries | 存入知识条目（title + content/file_id + source_type） |
| GET | /knowledge/entries | 获取当前用户知识条目列表（分页） |
| GET | /knowledge/entries/{id} | 获取单个知识条目详情 |
| DELETE | /knowledge/entries/{id} | 删除知识条目（PG + Milvus chunk） |
| POST | /knowledge/search | 检索知识库（query + top_k） |

### 存入统一流程

`POST /knowledge/entries` 是统一入口，后端流程：
1. 根据 source_type 获取文本（manual→直接取 content，file→通过 file_id 读取文件内容，research→直接取 content）
2. chunker 分块（title + "\n\n" + content → 递归字符分割，chunk_size=800, overlap=200）
3. embedding 批量编码所有 chunks → dense 向量
4. 插入 Milvus（text 字段触发 BM25 自动生成 sparse 向量）
5. 写 PG knowledge_entry 记录

## Chat Agent 工具体系

### 工具列表

| 工具 | 说明 | 触发场景 |
|------|------|---------|
| research | 深度研究（已有） | 需要搜索外部资源时 |
| knowledge_search | 知识库混合检索 | 用户问题可能命中已有知识时 |
| read_file | 根据 file_id 读取文件内容 | 聊天消息附带附件时 |
| save_to_knowledge | 将内容存入知识库 | 用户明确要求存入知识库时 |

### 系统提示词（新增规则）

```
你是一个知识助手。你可以：
1. 直接回答用户的简单问题
2. 调用 knowledge_search 检索已有知识库
3. 调用 research 进行深度研究
4. 调用 read_file 读取用户上传的附件内容
5. 调用 save_to_knowledge 将内容存入知识库

规则：
- 用户消息附带附件时，必须先调用 read_file 获取内容
- 根据用户意图决定是否调用 save_to_knowledge
- 用户说"存入知识库"、"记录下来"等类似意图时，调用 save_to_knowledge
- 对于非简单问题，优先调用 knowledge_search 查看是否有相关知识
- knowledge_search 有结果时，结合检索结果回答，无需再 research
- knowledge_search 无结果且需要深度研究时，再调用 research
```

### ChatState 扩展

```python
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: str
    research_result: Optional[str]
    research_active: bool
    file_ids: Optional[list[str]]      # 聊天附带的文件 ID 列表
```

### ChatStart 请求扩展

```python
class ChatStart(BaseModel):
    query: str
    thread_id: Optional[str] = None
    file_ids: Optional[list[str]] = None  # 附件文件 ID 列表
```

## 交互流程

### 流程 A：research 结果存入

```
用户提问 → Chat Agent → research → 返回最终答案
→ 前端展示结果 + "存入知识库"按钮
→ 用户点击按钮 → 弹出确认（可编辑 title）→ POST /knowledge/entries
```

### 流程 B：Chat 页面上传附件

```
用户上传文件 + 输入消息 → 前端先 POST /upload/file → 拿到 file_id
→ POST /chat/start { query, thread_id, file_ids }
→ Chat Agent 调用 read_file(file_id) → 获取内容注入上下文
→ LLM 判断意图：
  - 存入知识库 → 调用 save_to_knowledge(title, content)
  - 仅问答 → 基于文件内容回答
```

### 流程 C：知识库管理页面上传

```
用户在知识库页面上传文件 → POST /upload/file → 拿到 file_id
→ 填写表单（title 等）→ POST /knowledge/entries { source_type: "file", file_id, title }
```

### 流程 D：手动文本存入

```
用户在聊天中发送大段文本 + "存入知识库"
→ Chat Agent 调用 save_to_knowledge(title, content)
```

## 核心模块详细设计

### knowledge/embedding.py

- 使用 `langchain_community.embeddings.ZhipuAIEmbeddings`
- 环境变量：`ZHIPU_API_KEY`
- 模型：`embedding-3`，维度 2048
- 接口：`embed_texts(texts) -> list[list[float]]` + 异步版本

### knowledge/chunker.py

- 递归字符分块，默认 chunk_size=800, overlap=200
- 分割优先级：`\n\n`（段落）→ `\n`（行）→ 字符
- 每个 chunk 开头自动拼接 title 作为上下文
- 输出：`list[Chunk]`（text, index）

### knowledge/milvus.py

- `MilvusClient(uri=MILVUS_URI)`，应用启动时初始化
- 每个用户首次存入时自动创建 collection `knowledge_{user_id}`
- 提供 `get_or_create_collection(user_id)` 确保幂等

### knowledge/search.py

- 输入：query, user_id, top_k=5
- 步骤：GLM embedding 编码 query → 构造 dense_req + sparse_req → hybrid_search + RRFRanker → 返回结果列表

### knowledge/service.py

- `save_entry(user_id, title, content, source_type, source_id)` → chunk → embed → milvus insert → PG write
- `delete_entry(user_id, entry_id)` → milvus delete by entry_id → PG delete
- `list_entries(user_id, page, size)` → PG query
- `search(user_id, query, top_k)` → search.py

## 前端设计

### 新增路由

| 路径 | 守卫 | 页面 | 说明 |
|------|------|------|------|
| /knowledge | ProtectedRoute | KnowledgePage | 知识库管理主页面 |

### 组件清单

```
frontend/src/
├── pages/knowledge/
│   ├── KnowledgePage.tsx          # 知识库管理页（列表、搜索、删除）
│   └── AddKnowledgeModal.tsx      # 新增知识业务弹窗
├── components/
│   ├── Modal.tsx                  # 通用 Modal 壳（标题、插槽、确认/取消）
│   └── FileUploader.tsx           # 通用文件上传（拖拽/点击、进度、格式校验）
├── api/
│   ├── knowledgeApi.ts            # 知识库 API
│   └── uploadApi.ts               # 文件上传 API
└── types/
    └── knowledge.ts               # 类型定义
```

### Chat 页面改动

1. 搜索框区域新增附件上传按钮，选择文件后自动上传，显示附件标签
2. 发送消息时将 file_ids 附加到请求中
3. Research 结果卡片新增"存入知识库"按钮
4. 侧栏新增"知识库"导航入口

### 前端类型定义

```typescript
interface KnowledgeEntry {
  id: string;
  user_id: string;
  title: string;
  source_type: 'research' | 'manual' | 'file';
  source_id?: string;
  chunk_count: number;
  content_preview: string;
  create_at: string;
}

interface FileUploadRecord {
  id: string;
  file_name: string;
  file_format: string;
  file_size: number;
  create_at: string;
}

interface SearchResult {
  entry_id: string;
  chunk_index: number;
  text: string;
  score: number;
}
```

## 环境变量新增

```
MILVUS_URI=http://localhost:19530
ZHIPU_API_KEY=your_zhipu_api_key
UPLOAD_DIR=./uploads
```

## 依赖新增

```
pymilvus
zhipuai
charset-normalizer
PyPDF2
```

## 应用启动流程变更

`src/service/__init__.py` 的 lifespan 中新增：
1. 初始化 Milvus 连接 → `app.state.milvus_client`
2. 确保 `UPLOAD_DIR` 目录存在
