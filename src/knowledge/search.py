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
