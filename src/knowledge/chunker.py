"""
结构化文档分块器。
基于 DocumentElement[] 做语义分块，不依赖 Docling API。
"""

from typing import Optional

from src.config import ChunkConfig, DocumentElement, StructuredChunk


def chunk_structured(
    elements: list[DocumentElement],
    config: Optional[ChunkConfig] = None,
) -> list[StructuredChunk]:
    """
    基于 DocumentElement 列表做语义分块。
    标题作为分块边界不单独成块，挂入 heading_path；
    表格整块保留不拆分；连续段落合并直到超过 max_chunk_size。
    参数:
        elements: parser 产出的 DocumentElement 列表
        config: 分块配置，为 None 使用默认值
    返回:
        StructuredChunk 列表
    """
    if config is None:
        config = ChunkConfig()

    chunks: list[StructuredChunk] = []
    heading_path: list[str] = []
    current_text_parts: list[str] = []
    current_page_start: int = 1
    current_page_end: int = 1
    position = 0

    def _flush_paragraph() -> None:
        """将当前累积的段落文本刷出为一个 chunk。"""
        nonlocal position, current_text_parts, current_page_start, current_page_end

        if not current_text_parts:
            return

        merged = "\n\n".join(current_text_parts)
        if len(merged) > config.max_chunk_size:
            step = max(1, config.max_chunk_size - config.chunk_overlap)
            for i in range(0, len(merged), step):
                segment = merged[i : i + config.max_chunk_size]
                if segment.strip():
                    chunks.append(
                        StructuredChunk(
                            text=segment,
                            chunk_index=len(chunks),
                            page_start=current_page_start,
                            page_end=current_page_end,
                            heading_path=list(heading_path),
                            content_type="text",
                            position=position,
                        )
                    )
                    position += 1
        else:
            if merged.strip():
                chunks.append(
                    StructuredChunk(
                        text=merged,
                        chunk_index=len(chunks),
                        page_start=current_page_start,
                        page_end=current_page_end,
                        heading_path=list(heading_path),
                        content_type="text",
                        position=position,
                    )
                )
                position += 1

        current_text_parts = []
        current_page_start = current_page_end

    for elem in elements:
        if elem.element_type == "heading":
            _flush_paragraph()

            if elem.text.strip():
                level = elem.heading_level
                while len(heading_path) >= level:
                    heading_path.pop()
                heading_path.append(elem.text.strip())

            current_page_start = elem.page_number
            current_page_end = elem.page_number
            continue

        if elem.element_type == "table":
            _flush_paragraph()

            if elem.text.strip():
                chunks.append(
                    StructuredChunk(
                        text=elem.text,
                        chunk_index=len(chunks),
                        page_start=elem.page_number,
                        page_end=elem.page_number,
                        heading_path=list(heading_path),
                        content_type="table",
                        table_id=elem.table_id,
                        position=position,
                    )
                )
                position += 1

            current_page_start = elem.page_number
            current_page_end = elem.page_number
            continue

        if elem.element_type == "image":
            _flush_paragraph()

            if elem.text.strip():
                chunks.append(
                    StructuredChunk(
                        text=elem.text,
                        chunk_index=len(chunks),
                        page_start=elem.page_number,
                        page_end=elem.page_number,
                        heading_path=list(heading_path),
                        content_type="image",
                        position=position,
                    )
                )
                position += 1

            current_page_start = elem.page_number
            current_page_end = elem.page_number
            continue

        if elem.element_type == "code":
            _flush_paragraph()

            if elem.text.strip():
                chunks.append(
                    StructuredChunk(
                        text=elem.text,
                        chunk_index=len(chunks),
                        page_start=elem.page_number,
                        page_end=elem.page_number,
                        heading_path=list(heading_path),
                        content_type="code",
                        position=position,
                    )
                )
                position += 1

            current_page_start = elem.page_number
            current_page_end = elem.page_number
            continue

        text = elem.text
        if not text.strip():
            continue
        page = elem.page_number

        if not current_text_parts:
            current_page_start = page
        current_page_end = page

        candidate = "\n\n".join(current_text_parts + [text])
        if config.merge_short_paragraphs and len(candidate) <= config.max_chunk_size:
            current_text_parts.append(text)
        else:
            if len(text) > config.max_chunk_size:
                _flush_paragraph()
                step = max(1, config.max_chunk_size - config.chunk_overlap)
                for i in range(0, len(text), step):
                    segment = text[i : i + config.max_chunk_size]
                    if segment.strip():
                        chunks.append(
                            StructuredChunk(
                                text=segment,
                                chunk_index=len(chunks),
                                page_start=page,
                                page_end=page,
                                heading_path=list(heading_path),
                                content_type="text",
                                position=position,
                            )
                        )
                        position += 1
            else:
                _flush_paragraph()
                current_text_parts = [text]
                current_page_start = page
                current_page_end = page

    _flush_paragraph()
    return chunks
