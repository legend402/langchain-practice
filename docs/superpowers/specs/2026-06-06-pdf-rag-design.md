# Spec：生产级 PDF RAG 处理方案

> 日期：2026-06-06
> 状态：已批准

## 1. 概述

将现有知识库的 PDF 处理从 PyPDF2 纯文本提取升级为生产级 RAG 方案，覆盖解析、结构还原、语义分块、Agent 工具封装、可溯源引用和全维度评测。

**核心选型：**

| 层次 | 技术 | 说明 |
|------|------|------|
| 解析 | Docling | 统一处理 PDF/DOCX/MD/HTML/图片等所有格式，替代现有 reader.py |
| 多模态 | GLM-4V-Flash | 免费，复用 ZHIPU_API_KEY，处理图表/扫描件兜底 |
| 中间表示 | `DocumentElement` 列表 | parser 单次遍历 DoclingDocument 输出的结构化元素序列 |
| 分块 | 自定义结构化分块器 | 基于 `DocumentElement` 列表做语义分块，不依赖 Docling API |
| 向量库 | Milvus v2 Collection | 扩展元数据字段（页码/章节/表格定位） |

## 2. 系统架构

### 数据流

```
文件上传 → Docling 解析 → 遍历一次输出 DocumentElement[] → 结构化分块 → ZhipuAI Embedding → Milvus v2
                                                                           ↓
Agent 回答 ← 溯源引用格式化 ← Agent 工具（检索/读页/抽表） ← 混合检索
```

### 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/knowledge/parser.py` | **新增** | 统一文档解析器（Docling + GLM-4V-Flash），单次遍历输出 `DocumentElement[]` + 缓存 |
| `src/knowledge/chunker.py` | **重写** | 结构化分块器（基于 `DocumentElement[]`，不依赖 Docling API） |
| `src/knowledge/milvus.py` | **修改** | 新增 v2 Collection + Schema |
| `src/knowledge/search.py` | **修改** | 返回结果携带元数据 |
| `src/knowledge/service.py` | **修改** | 适配新解析 + 分块流程 |
| `src/tools/knowledge_search.py` | **修改** | 增强返回溯源信息 |
| `src/tools/read_pages.py` | **新增** | 按页码读原文工具 |
| `src/tools/extract_tables.py` | **新增** | 表格抽取工具 |
| `src/utils/reader.py` | **废弃** | 被 parser.py 替代 |
| `src/config.py` | **修改** | 新增 StructuredChunk 等数据模型 |
| `scripts/eval_rag.py` | **新增** | 评测脚本 |

## 3. 解析层

### 3.1 DocumentParser（`src/knowledge/parser.py`）

统一解析所有格式。**核心设计：parser 对 DoclingDocument 做唯一一次遍历**，同时完成：
1. 结构化元素提取 → 输出 `DocumentElement[]`（中间表示）
2. 表格/图片缓存 → 写文件系统
3. 图片描述 → GLM-4V-Flash 调用

#### 3.1.1 ParsedDocument（输出）

```python
@dataclass
class ParsedDocument:
    title: str                       # 文档标题
    file_path: str                   # 原始文件路径
    file_type: str                   # 文件类型（pdf/docx/md/html...）
    page_count: int                  # 总页数
    elements: list[DocumentElement]  # 结构化元素序列（单次遍历产出）
    metadata: dict                   # 文档级元数据
```

#### 3.1.2 DocumentElement（中间表示）

parser 单次遍历 `iterate_items()` 后产出的扁平元素序列，chunker 直接基于此做分块，不再接触 Docling API：

```python
@dataclass
class DocumentElement:
    element_type: str         # heading / paragraph / table / image / code
    text: str                 # 文本内容（表格为 Markdown，图片为描述文本）
    page_number: int          # 所在页码
    heading_level: int        # 标题层级（仅 heading 类型有效，1=H1, 2=H2...）
    table_id: str | None      # 表格唯一标识（仅 table 类型，如 T-001）
    table_page: int | None    # 表格所在页码（用于 tables_meta.json）
```

#### 3.1.3 解析流程

1. 根据文件类型选择 Docling pipeline（standard / vlm）
2. Docling 解析为 DoclingDocument
3. 提取图片，批量调用 GLM-4V-Flash 生成图片描述（`image_descriptions` dict）
4. **单次遍历** `iterate_items()`，按元素类型产出 `DocumentElement[]`：
   - `SectionHeaderItem` → `DocumentElement(element_type="heading", text=..., heading_level=element.level)`
   - 普通段落 → `DocumentElement(element_type="paragraph", text=...)`
   - `TableItem` → `DocumentElement(element_type="table", text=markdown, table_id=...)`，同时写缓存文件
   - `PictureItem` → `DocumentElement(element_type="image", text=描述文本)`
   - `CodeItem` → `DocumentElement(element_type="code", text=...)`
5. 空表格（图片型）→ 从页面截图裁剪 → GLM-4V-Flash 还原内容
6. 缓存 full.md + tables/ + image_descriptions.json 到文件系统

### 3.2 多模态处理

**GLM-4V-Flash 调用参数：**

- model: `glm-4v-flash`
- API Key: 复用 `ZHIPU_API_KEY`（环境变量已有）
- prompt: "请详细描述这张图片的内容，包括图表中的数据和趋势。如果是流程图，请描述流程步骤。"
- 图片输入: PDF 页面渲染为 JPEG（≤5MB，≤6000×6000）
- SDK: 复用 `zhipuai` Python 包（项目已有依赖）
- 并发: `asyncio.Semaphore(5)` 控制并发，`run_in_executor` 适配同步 SDK

### 3.3 空表格处理（图片型表格）

Docling 布局分析能识别表格位置（bbox），但图片型表格结构识别会失败（`num_rows=0, num_cols=0`）。处理策略：

1. 检测 `TableItem.data.num_rows == 0` 且 `export_to_markdown()` 为空
2. 从 `page_item.image.pil_image` 裁剪表格区域（需开启 `generate_page_images=True`）
3. 坐标转换：Docling 使用 BOTTOMLEFT 坐标系（Y 向上），PIL 使用 top-down（Y 向下）
   - 使用 `page_item.size.height`（PDF point 单位）做 Y 翻转，不是 PIL 像素高度
   - 缩放比例 = `pil_page.height / pdf_page_h`
4. 裁剪后图片交给 GLM-4V-Flash 还原表格内容

### 3.4 解析结果缓存

解析后将结构化内容缓存到文件系统，供 Agent 工具按需读取：

```
{UPLOAD_DIR}/parsed/{entry_id}/
  ├── full.md                # 完整 Markdown（docling_doc.export_to_markdown()）
  ├── image_descriptions.json # 图片描述字典
  └── tables/
      ├── T-001.md           # 表格 Markdown
      ├── T-002.md
      └── tables_meta.json   # 表格元数据（页码、caption、字符数）
```

> **注意**：取消按页缓存（`pages/` 目录）。DoclingDocument 没有按页导出 API，且 `read_pages` 工具可改为基于 `DocumentElement` 的 `page_number` 过滤实现。

## 4. 分块层

### 4.1 StructuredChunk 数据模型

```python
@dataclass
class StructuredChunk:
    text: str                        # chunk 文本内容
    chunk_index: int                 # chunk 序号
    page_start: int                  # 起始页码
    page_end: int                    # 结束页码
    heading_path: list[str]          # 标题路径，如 ["第2章", "2.1 概述"]
    content_type: str                # text / table / image / code
    table_id: str | None             # 表格唯一标识（如有）
    position: int                    # 文档内位置序号
```

### 4.2 分块器设计

`chunk_structured(elements: list[DocumentElement], config) -> list[StructuredChunk]`

**chunker 不依赖任何 Docling API**，输入是 parser 产出的 `DocumentElement[]` 扁平序列。遍历该序列按语义边界拆分：

| 元素类型 | 处理方式 |
|---------|---------|
| heading | 作为分块边界，不单独成块，挂入 heading_path；heading_level 维护层级树 |
| paragraph | 连续段落合并，直到超过 `max_chunk_size` |
| table | **整个表格为独立 chunk**，不拆分，保证结构完整 |
| image | 作为独立 chunk，content_type = image |
| code | 作为独立 chunk，content_type = code |

### 4.3 分块参数

```python
@dataclass
class ChunkConfig:
    max_chunk_size: int = 1000       # 最大字符数
    chunk_overlap: int = 100         # 重叠字符数（仅段落间）
    keep_table_intact: bool = True   # 表格不拆分
    merge_short_paragraphs: bool = True  # 合并短段落
```

## 5. Milvus Schema（v2 Collection）

```python
fields = [
    FieldSchema("id", DataType.VARCHAR, max_length=64, is_primary=True),
    FieldSchema("entry_id", DataType.VARCHAR, max_length=64),
    FieldSchema("chunk_index", DataType.INT64),
    FieldSchema("text", DataType.VARCHAR, max_length=8192),
    # 新增元数据字段
    FieldSchema("page_start", DataType.INT64),
    FieldSchema("page_end", DataType.INT64),
    FieldSchema("heading_path", DataType.VARCHAR, max_length=512),  # JSON 字符串
    FieldSchema("content_type", DataType.VARCHAR, max_length=32),   # text/table/image/code
    FieldSchema("table_id", DataType.VARCHAR, max_length=64),       # 可为空
    # 向量字段
    FieldSchema("dense_vector", DataType.FLOAT_VECTOR, dim=2048),
    FieldSchema("sparse_vector", DataType.SPARSE_FLOAT_VECTOR),
]
```

索引策略与 v1 一致：dense 向量 IVF_FLAT (IP) + sparse 向量 SPARSE_INVERTED_INDEX (BM25)。

## 6. Agent 工具层

### 6.1 knowledge_search（增强版）

在现有工具基础上增强返回值，携带溯源元数据：

```python
@tool
async def knowledge_search(query: str, knowledge_base_id: str, top_k: int = 5) -> list[dict]:
    """知识库语义检索，返回带溯源信息的结果。"""
    # 返回结构：
    # {
    #   "text": "chunk 文本",
    #   "score": 0.92,
    #   "page_range": [3, 4],
    #   "heading_path": ["第2章", "2.1"],
    #   "content_type": "text",
    #   "entry_id": "xxx",
    #   "entry_title": "文档标题"
    # }
```

### 6.2 read_pages（新增）

```python
@tool
async def read_pages(entry_id: str, page_start: int, page_end: int) -> str:
    """读取指定文档的指定页码范围的原始内容（Markdown 格式）。"""
    # 从 {UPLOAD_DIR}/parsed/{entry_id}/pages/ 读取并拼接
```

### 6.3 extract_tables（新增）

```python
@tool
async def extract_tables(entry_id: str, page_number: int | None = None, keyword: str | None = None) -> list[str]:
    """
    从文档中抽取表格。
    page_number: 指定页码的表格
    keyword: 按关键词匹配表格标题/上下文
    """
    # 从 {UPLOAD_DIR}/parsed/{entry_id}/tables/ 读取
```

### 6.4 溯源引用

通过 system prompt 约束 Agent 回答时附注来源，引用信息来自检索结果的元数据。

引用格式：`（来源：《文档标题》第X页 "章节名"）`

表格引用格式：`（来源：《文档标题》第X页 表格T-001）`

## 7. 迁移策略（双 Collection 过渡）

### 阶段一：部署新 Collection

1. 创建新 Collection `knowledge_v2`（带元数据字段）
2. 部署新的解析 + 分块代码
3. 代码通过配置开关选择读 v1 还是 v2 Collection

### 阶段二：新数据走新流程

1. 新上传的文档全部走 Docling 解析 → 结构化分块 → 写入 v2
2. 现有数据仍在 v1 中正常使用

### 阶段三：后台迁移旧数据

1. 遍历 v1 中的所有 entry，获取原始文件路径
2. 用新流程重新解析和分块，写入 v2
3. 验证迁移完整性（entry 数量、chunk 数量、元数据完整性）
4. 切换读取到 v2

### 阶段四：清理

1. 确认无问题后删除 v1 Collection
2. 移除兼容代码和配置开关
3. 更新记忆文件

## 8. 评测方案

### 8.1 评测数据

从公开网络下载不同类型的真实 PDF：

| 类型 | 来源 | 特点 |
|------|------|------|
| 学术论文 | arXiv | 双栏、公式、图表、参考文献 |
| 技术文档 | RFC / 开源项目文档 | 标题层级深、代码块多 |
| 政府报告 | .gov 公开报告 | 扫描件 + 表格 |
| 财务报表 | 上市公司公开年报 | 大量复杂表格 |
| 产品手册 | 开源项目文档 PDF | 图文混排、表格 |

### 8.2 性能评测

| 指标 | 测量方式 | 目标 |
|------|---------|------|
| 解析耗时 | 100 页 PDF 的端到端解析时间 | < 60s |
| 分块耗时 | 10 万字文档的分块时间 | < 5s |
| OCR 字准确率 | 人工抽检 50 页扫描件 OCR 结果 | > 95% |
| 内存峰值 | 解析 100 页 PDF 时的 RSS | < 2GB |

### 8.3 检索质量评测

每份 PDF 标注 20-30 个 (query, relevant_chunks) 对：

| 指标 | 说明 | 目标 |
|------|------|------|
| Recall@5 | Top 5 结果的召回率 | > 80% |
| Precision@3 | Top 3 结果的精确率 | > 70% |
| MRR | 平均倒数排名 | > 0.7 |
| vs 现有方案 | Recall@5 对比提升 | > 20% |

### 8.4 溯源引用评测

| 指标 | 说明 | 目标 |
|------|------|------|
| 页码准确率 | 引用页码与实际内容位置一致 | > 90% |
| 章节准确率 | heading_path 与实际章节匹配 | > 90% |
| 表格定位率 | 能通过 table_id 找到对应表格 | 100% |

### 8.5 评测实现

`scripts/eval_rag.py`：自动下载评测 PDF → 运行解析 → 检索评测 → 溯源评测 → 生成报告。

## 9. 新增依赖

```
docling>=2.0.0          # 文档解析
zhipuai                 # GLM-4V-Flash 调用（项目已有）
```

Docling 会自动安装 Tesseract OCR 相关依赖。
