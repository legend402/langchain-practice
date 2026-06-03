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
