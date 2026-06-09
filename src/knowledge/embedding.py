import os
from langchain_openai import OpenAIEmbeddings 

_embeddings: OpenAIEmbeddings | None = None

def get_embeddings() -> OpenAIEmbeddings:
  """
    获取 ZhipuAIEmbeddings 单例。
    使用 embedding-3 模型，维度 2048。
  """
  global _embeddings
  if _embeddings is None:
    _embeddings = OpenAIEmbeddings(
      model="embedding-3",
      base_url="https://open.bigmodel.cn/api/paas/v4/",
      api_key=os.getenv("ZHIPU_API_KEY"),
    )
  return _embeddings

def embed_texts(texts: list[str]) -> list[list[float]]:
  """
    批量文本向量化。
    参数:
        texts: 待编码的文本列表
    返回:
        向量列表，每个向量维度为 2048
  """
  return get_embeddings().embed_documents(texts)

async def aembed_texts(texts: list[str]) -> list[list[float]]:
  """
    异步批量文本向量化。
    参数:
        texts: 待编码的文本列表
    返回:
        向量列表，每个向量维度为 2048
  """
  return await get_embeddings().aembed_documents(texts)

def embed_query(text: str) -> list[float]:
  """
    单条查询文本向量化。
    参数:
        text: 查询文本
    返回:
        向量，维度为 2048
  """
  return get_embeddings().embed_query(text)

async def aembed_query(text: str) -> list[float]:
  """
    异步单条查询文本向量化。
    参数:
        text: 查询文本
    返回:
        向量，维度为 2048
  """
  return await get_embeddings().aembed_query(text)
