"""
混合检索模块。
支持 v1（基础）和 v2（带元数据）两种检索模式，
使用 dense + BM25 混合检索，RRF 融合排序。
"""

import json
from dataclasses import dataclass

from pymilvus import AnnSearchRequest, RRFRanker

from src.knowledge.embedding import embed_query
from src.knowledge.milvus import get_milvus_client, get_or_create_collection, get_or_create_v2_collection


@dataclass
class SearchHit:
    """基础检索结果。"""
    entry_id: str
    chunk_index: int
    text: str
    score: float


@dataclass
class StructuredSearchHit:
    """
    带元数据的检索结果。
    参数:
        entry_id: 知识条目 ID
        chunk_index: chunk 序号
        text: chunk 文本
        score: 相关度分数
        page_start: 起始页码
        page_end: 结束页码
        heading_path: 标题路径
        content_type: 内容类型
        table_id: 表格 ID（如有）
    """
    entry_id: str
    chunk_index: int
    text: str
    score: float
    page_start: int = 1
    page_end: int = 1
    heading_path: list[str] | None = None
    content_type: str = "text"
    table_id: str | None = None


def hybrid_search(
    query: str,
    user_id: str,
    top_k: int = 5,
) -> list[SearchHit]:
    """
    v1 混合检索：dense + BM25，RRF 融合排序。
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
        param={"metric_type": "IP", "params": {"radius": 0.5}},
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
            hits.append(
                SearchHit(
                    entry_id=hit["entity"]["entry_id"],
                    chunk_index=hit["entity"]["chunk_index"],
                    text=hit["entity"]["text"],
                    score=hit["distance"],
                )
            )
    return hits


def hybrid_search_v2(
    query: str,
    user_id: str,
    top_k: int = 5,
) -> list[StructuredSearchHit]:
    """
    v2 混合检索：返回带页码、章节、类型等元数据的结果。
    参数:
        query: 查询文本
        user_id: 用户 ID
        top_k: 返回结果数量
    返回:
        StructuredSearchHit 列表
    """
    col_name = get_or_create_v2_collection(user_id)
    client = get_milvus_client()

    dense_vector = embed_query(query)

    dense_req = AnnSearchRequest(
        data=[dense_vector],
        anns_field="dense_vector",
        param={"metric_type": "IP", "params": {"radius": 0.5}},
        limit=top_k,
    )

    sparse_req = AnnSearchRequest(
        data=[query],
        anns_field="sparse_vector",
        param={"metric_type": "BM25"},
        limit=top_k,
    )

    output_fields = [
        "entry_id", "chunk_index", "text",
        "page_start", "page_end", "heading_path",
        "content_type", "table_id",
    ]

    results = client.hybrid_search(
        collection_name=col_name,
        reqs=[dense_req, sparse_req],
        ranker=RRFRanker(),
        limit=top_k,
        output_fields=output_fields,
    )

    hits: list[StructuredSearchHit] = []
    if results and results[0]:
        for hit in results[0]:
            entity = hit["entity"]
            heading_raw = entity.get("heading_path", "[]")
            try:
                heading_path = json.loads(heading_raw) if heading_raw else []
            except (json.JSONDecodeError, TypeError):
                heading_path = []

            hits.append(
                StructuredSearchHit(
                    entry_id=entity["entry_id"],
                    chunk_index=entity["chunk_index"],
                    text=entity["text"],
                    score=hit["distance"],
                    page_start=entity.get("page_start", 1),
                    page_end=entity.get("page_end", 1),
                    heading_path=heading_path,
                    content_type=entity.get("content_type", "text"),
                    table_id=entity.get("table_id") or None,
                )
            )
    return hits
