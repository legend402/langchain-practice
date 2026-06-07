"""
RAG 评测脚本。
评测维度：解析性能、分块质量、检索召回率、溯源准确性。
"""

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def eval_parse_performance(file_path: str) -> dict:
    """
    评测文档解析性能。
    参数:
        file_path: 待评测的文件路径
    返回:
        包含耗时、页数等指标的字典
    """
    from src.knowledge.parser import parse_document

    start = time.time()
    parsed = asyncio.run(parse_document(file_path, entry_id="eval_temp"))
    elapsed = time.time() - start

    return {
        "file": file_path,
        "parse_time_seconds": round(elapsed, 2),
        "page_count": parsed.page_count,
        "file_type": parsed.file_type,
        "title": parsed.title,
        "element_count": len(parsed.elements),
    }


def eval_chunk_quality(file_path: str) -> dict:
    """
    评测分块质量。
    参数:
        file_path: 待评测的文件路径
    返回:
        包含 chunk 数量、类型分布、大小统计的字典
    """
    from src.knowledge.parser import parse_document
    from src.knowledge.chunker import chunk_structured

    parsed = asyncio.run(parse_document(file_path, entry_id="eval_temp"))
    start = time.time()
    chunks = chunk_structured(parsed.elements)
    elapsed = time.time() - start

    type_counts = {}
    sizes = []
    for c in chunks:
        type_counts[c.content_type] = type_counts.get(c.content_type, 0) + 1
        sizes.append(len(c.text))

    return {
        "file": file_path,
        "chunk_count": len(chunks),
        "chunk_time_seconds": round(elapsed, 4),
        "type_distribution": type_counts,
        "chunk_size_min": min(sizes) if sizes else 0,
        "chunk_size_max": max(sizes) if sizes else 0,
        "chunk_size_avg": round(sum(sizes) / len(sizes), 1) if sizes else 0,
        "pages_covered": max((c.page_end for c in chunks), default=0),
    }


def eval_retrieval(
    user_id: str,
    queries: list[dict],
    top_k: int = 5,
) -> dict:
    """
    评测检索质量。
    参数:
        user_id: 用户 ID
        queries: 查询列表，每项包含 query 和 expected_chunk_indices
        top_k: 返回结果数
    返回:
        包含 Recall@K、MRR 等指标的字典
    """
    from src.knowledge.search import hybrid_search_v2

    recalls = []
    mrrs = []

    for q in queries:
        query_text = q["query"]
        expected = set(q.get("expected_chunk_indices", []))
        hits = hybrid_search_v2(query_text, user_id, top_k=top_k)

        retrieved_indices = set(h.chunk_index for h in hits)

        if expected:
            recall = len(retrieved_indices & expected) / len(expected)
            recalls.append(recall)

            mrr = 0.0
            for rank, h in enumerate(hits, 1):
                if h.chunk_index in expected:
                    mrr = 1.0 / rank
                    break
            mrrs.append(mrr)

    return {
        "query_count": len(queries),
        "avg_recall_at_k": round(sum(recalls) / len(recalls), 4) if recalls else 0,
        "avg_mrr": round(sum(mrrs) / len(mrrs), 4) if mrrs else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="RAG 评测脚本")
    parser.add_argument("--file", type=str, help="待评测的文件路径")
    parser.add_argument("--user-id", type=str, help="用户 ID（检索评测用）")
    parser.add_argument("--queries", type=str, help="查询 JSON 文件路径（检索评测用）")
    args = parser.parse_args()

    results = {}

    if args.file:
        logger.info(f"评测解析性能: {args.file}")
        results["parse"] = eval_parse_performance(args.file)
        logger.info(f"评测分块质量: {args.file}")
        results["chunk"] = eval_chunk_quality(args.file)

    if args.user_id and args.queries:
        queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
        logger.info(f"评测检索质量: {len(queries)} 条查询")
        results["retrieval"] = eval_retrieval(args.user_id, queries)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
