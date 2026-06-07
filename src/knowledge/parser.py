"""
统一文档解析器。
使用 Docling 解析 PDF/DOCX/MD/HTML 等格式，
GLM-4V-Flash 处理图片描述，单次遍历输出 DocumentElement[] + 缓存。
DocumentConverter 全局单例，页面图片按需生成。
"""

import asyncio
import base64
import io
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument, PictureItem, TableItem

from src.config import DocumentElement

logger = logging.getLogger(__name__)

_UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

_converter: DocumentConverter | None = None
_page_image_converter: DocumentConverter | None = None
_page_image_cache: dict[str, dict[int, "object"]] = {}


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
) -> "object | None":
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
            pages_cache: dict[int, object] = {}
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


@dataclass
class ParsedDocument:
    """
    解析后的文档结构。
    参数:
        title: 文档标题
        file_path: 原始文件路径
        file_type: 文件类型
        page_count: 总页数
        elements: 结构化元素序列（单次遍历产出）
        metadata: 文档级元数据
    """

    title: str
    file_path: str
    file_type: str
    page_count: int
    elements: list[DocumentElement]
    metadata: dict = field(default_factory=dict)


def describe_image_with_glm4v(image_input: bytes) -> str:
    """
    调用 GLM-4V-Flash 生成图片描述。
    参数:
        image_input: 图片字节数据
    返回:
        图片的文本描述
    """
    from zhipuai import ZhipuAI

    client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))
    b64 = base64.b64encode(image_input).decode()
    image_url = f"data:image/jpeg;base64,{b64}"

    response = client.chat.completions.create(
        model="glm-4v-flash",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请详细描述这张图片的内容，包括图表中的数据和趋势。如果是流程图，请描述流程步骤。如果是表格截图，请还原表格内容。",
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    )

    content = response.choices[0].message.content
    if isinstance(content, list):
        return next(
            (
                item["text"]
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ),
            str(content),
        )
    return str(content)


async def _enrich_images(docling_doc: DoclingDocument) -> dict[str, str]:
    """
    提取文档中的图片并使用 GLM-4V-Flash 生成描述。
    使用 asyncio.Semaphore 控制并发，run_in_executor 适配同步 SDK。
    参数:
        docling_doc: Docling 文档对象
    返回:
        图片 self_ref → 描述文本 的字典
    """
    descriptions: dict[str, str] = {}
    semaphore = asyncio.Semaphore(5)

    async def _process_one(pic: PictureItem):
        self_ref = getattr(pic, "self_ref", None)
        if self_ref is None:
            return

        caption_text = ""
        try:
            caption_text = pic.caption_text(doc=docling_doc) or ""
        except Exception:
            pass

        if caption_text and len(caption_text.strip()) > 10:
            descriptions[self_ref] = caption_text.strip()
            return

        image_item = getattr(pic, "image", None)
        if image_item is None:
            return
        try:
            pil_img = image_item.pil_image
            if pil_img is None:
                return
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
        except Exception as e:
            logger.warning(f"图片提取失败: {e}")
            return

        async with semaphore:
            loop = asyncio.get_running_loop()
            desc = await loop.run_in_executor(
                None, lambda: describe_image_with_glm4v(img_bytes)
            )
        if desc:
            descriptions[self_ref] = desc

    tasks = [
        _process_one(pic) for pic in (getattr(docling_doc, "pictures", None) or [])
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    return descriptions


def _get_page_number(item: object) -> int:
    """
    获取 Docling 元素所在页码。
    参数:
        item: Docling 文档元素
    返回:
        页码（从 1 开始），获取失败返回 1
    """
    try:
        prov = getattr(item, "prov", None)
        if prov and len(prov) > 0:
            return prov[0].page_no
    except (AttributeError, IndexError, TypeError):
        pass
    return 1


def _extract_table_image(
    pil_page: "object",
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
                logger.info(f"空表格 {table_id} 跳过图片还原（页 {page}）")

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
        await progress_callback("parsing", "Docling 解析中...")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: converter.convert(path),
    )
    docling_doc = result.document

    if progress_callback:
        await progress_callback("enriching_images", "图片描述生成中...")

    image_descriptions = await _enrich_images(docling_doc)

    if progress_callback:
        await progress_callback("walking_cache", "结构化遍历与缓存中...")

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
