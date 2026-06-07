"""
知识库 v1 → v2 迁移脚本。
遍历 v1 中的所有 entry，重新解析和分块，写入 v2 Collection。
使用方式: python scripts/migrate_knowledge_v1_to_v2.py --user-id <USER_ID>
"""

import argparse
import asyncio
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_user(user_id: str) -> dict:
    """
    迁移指定用户的所有知识条目。
    参数:
        user_id: 用户 ID
    返回:
        迁移统计信息
    """
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession
    from src.service.db.database import engine
    from src.service.db.db import KnowledgeEntry, FileUpload
    from src.knowledge.parser import parse_document
    from src.knowledge.chunker import chunk_structured
    from src.knowledge.embedding import aembed_texts
    from src.knowledge.milvus import get_or_create_v2_collection, get_milvus_client

    stats = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "errors": []}
    col_name = get_or_create_v2_collection(user_id)
    client = get_milvus_client()

    async with AsyncSession(engine) as session:
        result = await session.exec(
            select(KnowledgeEntry).where(KnowledgeEntry.user_id == user_id)
        )
        entries = result.all()

    stats["total"] = len(entries)
    logger.info(f"开始迁移 {len(entries)} 个知识条目...")

    for entry in entries:
        try:
            async with AsyncSession(engine) as session:
                file_record = await session.exec(
                    select(FileUpload).where(FileUpload.id == entry.source_id)
                )
                file_record = file_record.first()

            if not file_record or not os.path.exists(file_record.file_path):
                logger.warning(f"跳过 {entry.id}: 原始文件不存在")
                stats["skipped"] += 1
                continue

            parsed = await parse_document(file_record.file_path, entry_id=entry.id)
            chunks = chunk_structured(parsed.elements)

            if not chunks:
                logger.warning(f"跳过 {entry.id}: 解析后无内容")
                stats["skipped"] += 1
                continue

            chunk_texts = [c.text for c in chunks]
            vectors = await aembed_texts(chunk_texts)

            data = []
            for chunk, vector in zip(chunks, vectors):
                data.append({
                    "entry_id": entry.id,
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
            stats["migrated"] += 1
            logger.info(f"已迁移 {entry.id}: {len(chunks)} 个 chunks")

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append({"entry_id": entry.id, "error": str(e)})
            logger.error(f"迁移失败 {entry.id}: {e}")

    logger.info(
        f"迁移完成: 总计 {stats['total']}, "
        f"成功 {stats['migrated']}, "
        f"跳过 {stats['skipped']}, "
        f"失败 {stats['failed']}"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="知识库 v1 → v2 迁移")
    parser.add_argument("--user-id", required=True, help="用户 ID")
    args = parser.parse_args()

    stats = asyncio.run(migrate_user(args.user_id))
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
