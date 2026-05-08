import os
from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils import get_setting_config

def init_embedding_model():
  config = get_setting_config()
  return ZhipuAIEmbeddings(
    model="embedding-3",
    api_key=config.glm_api_key,
    dimensions=1024
  )

def get_chunks(text):
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
  chunks = text_splitter.split_text(text)
  return chunks

class FAISSProcessor:
  @staticmethod
  def vector_store(text_chunks):
    embedding = init_embedding_model()
    # embedding-3 的单条请求最多支持 3072 个Tokens，且数组最大不得超过 64 条
    batch_size = 64
    store = FAISS

    for i in range(0, len(text_chunks), batch_size):
      chunk = text_chunks[i:i+batch_size]
      if i == 0:
        store = FAISS.from_texts(chunk, embedding)
      else:
        store.add_texts(chunk)
    store.save_local("faiss_db")

  @staticmethod
  def check_database_exists():
    """检查数据库是否存在"""
    return os.path.exists("faiss_db") and os.path.exists("faiss_db/index.faiss")
