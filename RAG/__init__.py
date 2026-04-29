import os
from langchain_community.embeddings import ZhipuAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from utils import get_setting_config

def init_embedding_model():
  config = get_setting_config()
  return ZhipuAIEmbeddings(
    model="embedding-3",
    api_key=config.embeddings_api_key
  )

def get_chunks(text):
  text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
  chunks = text_splitter.split_text(text)
  return chunks

def vector_store(text_chunks):
  embedding = init_embedding_model()
  vector_store = FAISS.from_texts(text_chunks, embedding)
  print(f'=========向量数据库创建成功===========')
  vector_store.save_local("faiss_db")

def check_database_exists():
  """检查数据库是否存在"""
  return os.path.exists("faiss_db") and os.path.exists("faiss_db/index.faiss")