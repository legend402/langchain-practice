# PDF 上传性能优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 PDF 上传解析从同步阻塞 ~337s 优化为异步任务队列 + SSE 进度推送，结合 DocumentConverter 单例、按需页面图片、Embedding 批量并发等多维优化。

**Architecture:** 上传请求立即返回 task_id，后台 asyncio.Task 执行 Docling 解析，前端通过 SSE 轮询进度（解析中/分块中/向量化中/完成）。DocumentConverter 作为应用级单例在 lifespan 启动时预热，页面图片按需生成，Embedding 按 64/batch 并发请求。

**Tech Stack:** asyncio.Task + Redis 进度缓存 + SSE (复用现有 StreamingResponse 模式) + Docling 2.97 + ZhipuAI embedding-3

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/knowledge/parser.py` | DocumentConverter 单例 + 启动预热 + 按需页面图片 + OCR 按需 |
| `src/knowledge/embedding.py` | 新增 `aembed_texts_batched()` 64/batch 并发 |
| `src/knowledge/service.py` | 新增 `save_entry_v2_async()` 异步任务版 |
| `src/service/routes/knowledge.py` | 新增 SSE 进度推送路由 + 异步上传入口 |
| `src/service/routes/sse.py` | 无修改（已有 SSE 模式可复用） |
| `src/service/__init__.py` | lifespan 中预热 Docling converter |
| `src/service/db/redis.py` | 无修改（已有 Redis 客户端） |
| `src/config.py` | 新增 `TASK_KEY_PREFIX` 等常量 |

---

## 依赖关系

```
Task 1 (config.py)
Task 2 (parser.py 单例+预热) ──→ Task 4 (service.py 异步任务)
Task 3 (embedding.py 批量)  ──→ Task 4 (service.py 异步任务)
Task 4 ──→ Task 5 (routes SSE)
Task 5 ──→ Task 6 (lifespan 预热)
```

---

### Task 1: config.py 新增任务状态常量

**Files:**
- Modify: `src/config.py:217` (文件末尾追加)

- [ ] **Step 1: 追加任务状态枚举和 Redis key 前缀常量**

在 `src/config.py` 文件末尾追加：

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/config.py
git commit -m "feat: 添加解析任务状态常量和 Redis key 前缀"
```

---

### Task 2: parser.py — DocumentConverter 单例 + 按需页面图片 + OCR 按需

**Files:**
- Modify: `src/knowledge/parser.py` (全文件重构)

当前 `parse_document()` 每次调用都创建新的 `DocumentConverter()`（耗时 ~7s 加载 770 个权重），且 `generate_page_images=True, images_scale=2.0` 为所有页面生成高分辨率图片（最大开销）。

改造目标：
1. **DocumentConverter 单例**：模块级 `_converter` 变量 + `get_converter()` 懒初始化
2. **基础转换不含页面图片**：`generate_page_images=False, generate_picture_images=True, images_scale=1.0`
3. **按需生成页面图片**：新增 `generate_page_image(docling_doc, page_no) -> PIL.Image` 函数，仅当 `_extract_table_image()` 需要裁剪时调用
4. **OCR 按需**：基础 `do_ocr=False`，新增 `parse_with_ocr()` 可选用 OCR 的入口
5. **`converter.convert()` 放入 `run_in_executor`** 不阻塞事件循环

- [ ] **Step 1: 添加 DocumentConverter 单例和预热函数**

在 `parser.py` 文件顶部（imports 之后，`_UPLOAD_DIR` 之后）添加：

```python
_converter: DocumentConverter | None = None
_page_image_converter: DocumentConverter | None = None


def _build_converter() -> DocumentConverter:
    """
    构建 DocumentConverter 实例。
    基础配置：不生成页面图片、不开启 OCR、图片缩放 1.0。
    """
    pipeline_options = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=True,
        generate_picture_images=True,
        generate_page_images=False,
        images_scale=1.0,
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def get_converter() -> DocumentConverter:
    """
    获取 DocumentConverter 全局单例。
    参数:
        无
    返回:
        DocumentConverter 实例
    """
    global _converter
    if _converter is None:
        _converter = _build_converter()
    return _converter


async def warmup_converter() -> None:
    """
    预热 DocumentConverter（加载模型权重）。
    在 FastAPI lifespan 启动时调用，避免首次请求延迟。
    """
    get_converter()
    logger.info("DocumentConverter 预热完成")
```

- [ ] **Step 2: 添加按需页面图片生成函数**

在 `_get_page_number()` 函数之后添加：

```python
_page_image_cache: dict[str, dict[int, "PIL.Image.Image"]] = {}


def _get_page_image_converter() -> DocumentConverter:
    """
    获取用于生成页面图片的 DocumentConverter 单例。
    独立于主 converter，配置 generate_page_images=True。
    """
    global _page_image_converter
    if _page_image_converter is None:
        pipeline_options = PdfPipelineOptions(
            do_ocr=False,
            do_table_structure=False,
            generate_picture_images=False,
            generate_page_images=True,
            images_scale=2.0,
        )
        _page_image_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
    return _page_image_converter


async def generate_page_image(
    docling_doc: DoclingDocument,
    page_no: int,
    source_path: str | None = None,
) -> "PIL.Image.Image | None":
    """
    按需为指定页面生成高分辨率图片。
    使用缓存避免重复转换：同一 source_path 只转换一次，后续从缓存取页面图片。
    参数:
        docling_doc: 已解析的 Docling 文档对象
        page_no: 页码（1-based）
        source_path: 原始文件路径（用于缓存 key 和按需转换）
    返回:
        PIL Image 对象，失败返回 None
    """
    cache_key = source_path or ""

    if cache_key and cache_key in _page_image_cache:
        cached = _page_image_cache[cache_key].get(page_no)
        if cached is not None:
            return cached

    try:
        page_item = (docling_doc.pages or {}).get(page_no)
        if page_item is not None and hasattr(page_item, "image") and page_item.image is not None:
            return page_item.image.pil_image
    except Exception:
        pass

    if not source_path or not Path(source_path).exists():
        return None

    try:
        converter = _get_page_image_converter()

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: converter.convert(Path(source_path)),
        )

        if cache_key:
            pages_cache: dict[int, "PIL.Image.Image"] = {}
            for pn, pi in (result.document.pages or {}).items():
                if hasattr(pi, "image") and pi.image is not None:
                    pages_cache[pn] = pi.image.pil_image
            _page_image_cache[cache_key] = pages_cache

        page_item_new = (result.document.pages or {}).get(page_no)
        if page_item_new and hasattr(page_item_new, "image") and page_item_new.image is not None:
            return page_item_new.image.pil_image
    except Exception as e:
        logger.warning(f"按需生成页面图片失败 (page={page_no}): {e}")

    return None
```

- [ ] **Step 3: 修改 `_extract_table_image` 使用按需页面图片**

将现有 `_extract_table_image` 函数替换为接受 `pil_page` 参数，不再依赖 `docling_doc.pages`：

```python
def _extract_table_image(
    pil_page: "PIL.Image.Image",
    pdf_page_h: float,
    table_item: TableItem,
) -> bytes | None:
    """
    从页面图片中裁剪表格区域，返回 JPEG 字节。
    参数:
        pil_page: 页面的 PIL Image
        pdf_page_h: PDF 页面高度（用于坐标翻转）
        table_item: TableItem 元素
    返回:
        表格区域的 JPEG 字节，失败返回 None
    """
    try:
        prov = getattr(table_item, "prov", []) or []
        if not prov:
            return None
        bbox = prov[0].bbox

        l, t, r, b = bbox.l, bbox.t, bbox.r, bbox.b

        coord_str = str(getattr(bbox.coord_origin, "value", ""))
        if "BOTTOM" in coord_str:
            orig_t, orig_b = t, b
            t = pdf_page_h - orig_b
            b = pdf_page_h - orig_t
            if t > b:
                t, b = b, t

        scale = pil_page.height / pdf_page_h

        crop_box = (
            max(0, int(l * scale)),
            max(0, int(t * scale)),
            min(pil_page.width, int(r * scale)),
            min(pil_page.height, int(b * scale)),
        )
        if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
            return None

        cropped = pil_page.crop(crop_box)
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception as e:
        logger.warning(f"表格图片裁剪失败: {e}")
        return None
```

- [ ] **Step 4: 修改 `_walk_and_cache` 使用异步按需页面图片**

将 `_walk_and_cache` 改为 `async`，在遇到空表格时按需获取页面图片：

```python
async def _walk_and_cache(
    docling_doc: DoclingDocument,
    entry_id: str,
    image_descriptions: dict[str, str],
    source_path: str | None = None,
) -> list[DocumentElement]:
    """
    对 DoclingDocument 做唯一一次遍历，同时产出 DocumentElement[] 和缓存文件。
    空表格时按需生成页面图片并裁剪。
    参数:
        docling_doc: Docling 文档对象
        entry_id: 知识条目 ID（用于缓存路径）
        image_descriptions: 图片 self_ref → 描述文本的字典
        source_path: 原始文件路径（用于按需生成页面图片的缓存 key）
    返回:
        DocumentElement 列表
    """
    from docling_core.types.doc import CodeItem, SectionHeaderItem

    elements: list[DocumentElement] = []

    cache_dir = Path(_UPLOAD_DIR) / "parsed" / entry_id
    tables_dir = cache_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    try:
        md_full = docling_doc.export_to_markdown()
        (cache_dir / "full.md").write_text(md_full, encoding="utf-8")
    except Exception as e:
        logger.warning(f"缓存完整 Markdown 失败: {e}")

    tables_meta: list[dict] = []
    table_idx = 0

    for item, _level in docling_doc.iterate_items():
        page = _get_page_number(item)

        if isinstance(item, SectionHeaderItem):
            heading_text = str(getattr(item, "text", "")).strip()
            if heading_text:
                elements.append(
                    DocumentElement(
                        element_type="heading",
                        text=heading_text,
                        page_number=page,
                        heading_level=getattr(item, "level", 1),
                    )
                )
            continue

        if isinstance(item, TableItem):
            table_idx += 1
            table_id = f"T-{table_idx:03d}"

            table_md = ""
            try:
                table_md = item.export_to_markdown(doc=docling_doc) or ""
            except Exception:
                pass

            if not table_md.strip():
                page_image = await generate_page_image(docling_doc, page, source_path)
                if page_image is not None:
                    page_size = None
                    pages = getattr(docling_doc, "pages", {}) or {}
                    page_item = pages.get(page)
                    if page_item:
                        page_size = getattr(page_item, "size", None)
                    pdf_page_h = getattr(page_size, "height", 0) if page_size else 0

                    if pdf_page_h > 0:
                        img_bytes = _extract_table_image(page_image, pdf_page_h, item)
                        if img_bytes:
                            try:
                                table_md = describe_image_with_glm4v(img_bytes)
                            except Exception as e:
                                logger.warning(f"表格图片多模态还原失败: {e}")

            (tables_dir / f"{table_id}.md").write_text(table_md, encoding="utf-8")

            heading = ""
            try:
                heading = item.caption_text(doc=docling_doc) or ""
            except Exception:
                pass

            tables_meta.append({
                "table_id": table_id,
                "page_number": page,
                "heading": heading,
                "char_count": len(table_md),
            })

            if table_md.strip():
                elements.append(
                    DocumentElement(
                        element_type="table",
                        text=table_md,
                        page_number=page,
                        table_id=table_id,
                    )
                )
            continue

        if isinstance(item, PictureItem):
            self_ref = getattr(item, "self_ref", "")
            pic_text = image_descriptions.get(self_ref, "")
            if not pic_text:
                try:
                    pic_text = item.caption_text(doc=docling_doc) or ""
                except Exception:
                    pass
            if not pic_text:
                pic_text = str(getattr(item, "text", ""))
            if not pic_text:
                pic_text = "[图片]"

            if pic_text.strip():
                elements.append(
                    DocumentElement(
                        element_type="image",
                        text=pic_text,
                        page_number=page,
                    )
                )
            continue

        if isinstance(item, CodeItem):
            code_text = str(getattr(item, "text", ""))
            if code_text.strip():
                elements.append(
                    DocumentElement(
                        element_type="code",
                        text=code_text,
                        page_number=page,
                    )
                )
            continue

        text = str(getattr(item, "text", ""))
        if text.strip():
            elements.append(
                DocumentElement(
                    element_type="paragraph",
                    text=text,
                    page_number=page,
                )
            )

    (tables_dir / "tables_meta.json").write_text(
        json.dumps(tables_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return elements
```

- [ ] **Step 5: 重写 `parse_document` 使用单例 + run_in_executor**

```python
async def parse_document(
    file_path: str,
    entry_id: str,
    progress_callback: "callable | None" = None,
) -> ParsedDocument:
    """
    统一文档解析入口。
    使用全局单例 DocumentConverter，convert 在线程池执行不阻塞事件循环。
    参数:
        file_path: 原始文件路径
        entry_id: 知识条目 ID（用于缓存路径）
        progress_callback: 进度回调函数，接收 (status: str, detail: str)
    返回:
        ParsedDocument 结构化文档
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    suffix = path.suffix.lower()
    file_type = suffix.lstrip(".")

    converter = get_converter()

    if progress_callback:
        progress_callback("parsing", "Docling 解析中...")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: converter.convert(path),
    )
    docling_doc = result.document

    if progress_callback:
        progress_callback("enriching_images", "图片描述生成中...")

    image_descriptions = await _enrich_images(docling_doc)

    if progress_callback:
        progress_callback("walking_cache", "结构化遍历与缓存中...")

    elements = await _walk_and_cache(docling_doc, entry_id, image_descriptions, str(path))

    if image_descriptions:
        desc_path = Path(_UPLOAD_DIR) / "parsed" / entry_id / "image_descriptions.json"
        desc_path.write_text(
            json.dumps(image_descriptions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    title = path.stem
    try:
        if hasattr(docling_doc, "name") and docling_doc.name:
            title = docling_doc.name
    except Exception:
        pass

    page_count = 0
    try:
        page_count = len(docling_doc.pages)
    except Exception:
        pass

    metadata = {
        "file_name": path.name,
        "file_size": path.stat().st_size,
        "file_type": file_type,
        "image_descriptions": image_descriptions,
    }

    return ParsedDocument(
        title=title,
        file_path=str(file_path),
        file_type=file_type,
        page_count=page_count,
        elements=elements,
        metadata=metadata,
    )
```

- [ ] **Step 6: Commit**

```bash
git add src/knowledge/parser.py
git commit -m "refactor: DocumentConverter 单例 + 按需页面图片 + convert 异步化"
```

---

### Task 3: embedding.py — 新增批量并发向量化

**Files:**
- Modify: `src/knowledge/embedding.py`

当前 `aembed_texts()` 一次发送所有文本，ZhipuAI embedding-3 限制单次最多 64 条，超过会 400 错误。

- [ ] **Step 1: 新增 `aembed_texts_batched` 函数**

在 `embedding.py` 文件末尾追加：

```python
import asyncio

EMBED_BATCH_SIZE = 64


async def aembed_texts_batched(texts: list[str]) -> list[list[float]]:
    """
    分批异步向量化，每批 64 条，多批并发。
    参数:
        texts: 待编码的文本列表
    返回:
        向量列表，顺序与输入一致
    """
    if len(texts) <= EMBED_BATCH_SIZE:
        return await aembed_texts(texts)

    batches = [
        texts[i : i + EMBED_BATCH_SIZE]
        for i in range(0, len(texts), EMBED_BATCH_SIZE)
    ]

    semaphore = asyncio.Semaphore(3)

    async def _embed_batch(batch: list[str]) -> list[list[float]]:
        async with semaphore:
            return await aembed_texts(batch)

    results = await asyncio.gather(*[_embed_batch(b) for b in batches])

    vectors: list[list[float]] = []
    for batch_result in results:
        vectors.extend(batch_result)
    return vectors
```

- [ ] **Step 2: Commit**

```bash
git add src/knowledge/embedding.py
git commit -m "feat: 新增 aembed_texts_batched 64/batch 并发向量化"
```

---

### Task 4: service.py — 异步任务队列 + Redis 进度 + 文件哈希缓存

**Files:**
- Modify: `src/knowledge/service.py`

核心改造：`save_entry_v2_async()` 启动后台任务，立即返回 task_id，通过 Redis 推送进度。

- [ ] **Step 1: 新增异步任务管理函数**

在 `service.py` 的 imports 区块末尾追加：

```python
import hashlib
import asyncio
from src.config import PARSE_TASK_KEY_PREFIX, PARSE_TASK_TTL, ParseTaskStatus
from src.service.db.redis import get_redis
from src.knowledge.embedding import aembed_texts_batched
```

在 `search_knowledge_v2()` 函数之后追加以下函数：

```python
def _compute_file_hash(file_path: str) -> str:
    """
    计算文件的 SHA-256 哈希值。
    参数:
        file_path: 文件路径
    返回:
        哈希值十六进制字符串
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


async def _update_task_status(
    task_id: str,
    status: ParseTaskStatus,
    detail: str = "",
    entry_id: str = "",
) -> None:
    """
    更新 Redis 中的任务状态。
    参数:
        task_id: 任务 ID
        status: 任务状态
        detail: 状态描述
        entry_id: 关联的知识条目 ID
    """
    redis = get_redis()
    key = f"{PARSE_TASK_KEY_PREFIX}{task_id}"
    payload = {
        "status": status,
        "detail": detail,
        "entry_id": entry_id,
    }
    await redis.set(key, json.dumps(payload, ensure_ascii=False), ex=PARSE_TASK_TTL)


async def get_task_status(task_id: str) -> dict | None:
    """
    查询任务状态。
    参数:
        task_id: 任务 ID
    返回:
        任务状态字典（status/detail/entry_id），不存在返回 None
    """
    redis = get_redis()
    key = f"{PARSE_TASK_KEY_PREFIX}{task_id}"
    data = await redis.get(key)
    if data is None:
        return None
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


async def _run_parse_task(
    task_id: str,
    entry_id: str,
    file_path: str,
    user_id: UUID,
    title: str,
    source_type: str,
    source_id: str | None,
) -> None:
    """
    后台解析任务：解析 → 分块 → 向量化 → 存储。
    参数:
        task_id: 任务 ID
        entry_id: 知识条目 ID
        file_path: 文件路径
        user_id: 用户 ID
        title: 知识标题
        source_type: 来源类型
        source_id: 关联来源 ID
    """
    from src.knowledge.parser import parse_document
    from src.knowledge.chunker import chunk_structured

    try:
        async def progress_cb(status: str, detail: str):
            await _update_task_status(task_id, status, detail, entry_id)

        parsed = await parse_document(file_path, entry_id, progress_callback=progress_cb)

        await _update_task_status(task_id, "chunking", "结构化分块中...", entry_id)
        chunks = chunk_structured(parsed.elements)

        chunk_texts = [c.text for c in chunks]
        preview = (chunk_texts[0][:200] + "...") if chunk_texts and len(chunk_texts[0]) > 200 else (chunk_texts[0] if chunk_texts else "")

        await _update_task_status(task_id, "embedding", f"向量化中（{len(chunks)} 个分块）...", entry_id)
        vectors = await aembed_texts_batched(chunk_texts)

        await _update_task_status(task_id, "storing", "写入向量库...", entry_id)
        uid = str(user_id)
        col_name = get_or_create_v2_collection(uid)
        client = get_milvus_client()

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

        from src.service.db.database import engine as _engine
        async with AsyncSession(_engine) as session:
            entry = KnowledgeEntry(
                id=entry_id,
                user_id=user_id,
                title=title,
                source_type=source_type,
                source_id=source_id,
                chunk_count=len(chunks),
                content_preview=preview,
            )
            session.add(entry)
            await session.commit()

        await _update_task_status(task_id, "completed", "解析完成", entry_id)
    except Exception as e:
        logger.exception(f"解析任务失败 (task_id={task_id}): {e}")
        await _update_task_status(task_id, "failed", str(e), entry_id)


async def save_entry_v2_async(
    user_id: UUID,
    title: str,
    file_path: str,
    source_type: str = "file",
    source_id: str | None = None,
) -> str:
    """
    异步知识条目存入：立即返回 task_id，后台执行解析和存储。
    通过 get_task_status(task_id) 查询进度。
    参数:
        user_id: 用户 ID
        title: 知识标题
        file_path: 文件路径
        source_type: 来源类型
        source_id: 关联来源 ID
    返回:
        task_id（用于查询进度）
    """
    entry_id = str(uuid4())
    task_id = str(uuid4())

    await _update_task_status(task_id, "pending", "等待解析...", entry_id)

    asyncio.create_task(
        _run_parse_task(
            task_id=task_id,
            entry_id=entry_id,
            file_path=file_path,
            user_id=user_id,
            title=title,
            source_type=source_type,
            source_id=source_id,
        )
    )

    return task_id
```

- [ ] **Step 2: Commit**

```bash
git add src/knowledge/service.py
git commit -m "feat: 新增异步解析任务队列，Redis 进度推送 + Embedding 批量并发"
```

---

### Task 5: routes/knowledge.py — SSE 进度推送路由

**Files:**
- Modify: `src/service/routes/knowledge.py`

新增两个路由：
1. `POST /knowledge/entries/async` — 异步上传，返回 task_id
2. `GET /knowledge/tasks/{task_id}/progress` — SSE 进度流

- [ ] **Step 1: 新增异步上传路由和 SSE 进度路由**

在 `knowledge.py` 的 imports 区块修改：

```python
import asyncio
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from src.service.auth.deps import CurrentUser
from src.service.db.database import get_session
from src.service.result import Result
from src.knowledge.service import (
    save_entry_v2 as _save_entry,
    delete_entry_v2 as _delete_entry,
    list_entries as _list_entries,
    search_knowledge_v2 as _search_knowledge_v2,
    search_entries as _search_entries,
    save_entry_v2_async,
    get_task_status,
)
```

在文件末尾追加两个新路由：

```python
@router.post("/entries/async")
async def create_entry_async(
    body: CreateEntryRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    异步存入知识条目（PDF 等大文件）。
    立即返回 task_id，前端通过 SSE 轮询进度。
    """
    if not body.file_id:
        return Result.error("异步上传必须提供 file_id")

    from src.service.controller.FileUpload import get_file_record
    record = await get_file_record(session, file_id=body.file_id)
    if not record:
        return Result.error("文件记录不存在")

    task_id = await save_entry_v2_async(
        user_id=user.id,
        title=body.title,
        file_path=record.file_path,
        source_type=body.source_type,
        source_id=body.source_id or body.file_id,
    )
    return Result.success({"task_id": task_id})


@router.get("/tasks/{task_id}/progress")
async def task_progress(task_id: str):
    """
    SSE 推送解析任务进度。
    前端通过 EventSource 连接，实时接收状态更新。
    任务完成后自动断开。
    """

    async def _stream():
        last_status = None
        while True:
            status = await get_task_status(task_id)
            if status is None:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break

            if status != last_status:
                yield f"data: {json.dumps(status)}\n\n"
                last_status = dict(status)

            if status.get("status") in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(_stream(), media_type="text/event-stream")
```

- [ ] **Step 2: Commit**

```bash
git add src/service/routes/knowledge.py
git commit -m "feat: 新增异步上传路由和 SSE 进度推送"
```

---

### Task 6: lifespan 预热 Docling Converter

**Files:**
- Modify: `src/service/__init__.py`

在 lifespan 启动阶段调用 `warmup_converter()`，预加载 770 个模型权重。

- [ ] **Step 1: 在 lifespan 中添加预热调用**

在 `src/service/__init__.py` 的 imports 区块追加：

```python
from src.knowledge.parser import warmup_converter
```

在 `lifespan()` 函数内，`get_milvus_client()` 之后、`yield` 之前追加：

```python
    await warmup_converter()
```

- [ ] **Step 2: Commit**

```bash
git add src/service/__init__.py
git commit -m "feat: lifespan 启动时预热 DocumentConverter 模型权重"
```

---

### Task 7: 更新记忆文件

**Files:**
- Modify: `.opencode/memory/backend.md`

- [ ] **Step 1: 更新 backend.md 中知识库部分，反映异步任务队列和性能优化**

在知识库引擎相关描述中补充：
- DocumentConverter 全局单例 + 启动预热
- 按需页面图片生成（`generate_page_images=False`，裁剪表格时按需生成）
- Embedding 64/batch 并发（`aembed_texts_batched`）
- 异步任务队列：`save_entry_v2_async()` → `task_id` → SSE 进度推送
- Redis 存储任务状态（`parse_task:{task_id}`）

- [ ] **Step 2: Commit**

```bash
git add .opencode/memory/backend.md
git commit -m "docs: 更新记忆文件反映性能优化变更"
```
