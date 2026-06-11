# 基于语义相似度拆分文本的示例
from dotenv import load_dotenv
from langchain_experimental.text_splitter import SemanticChunker

from src.knowledge.embedding import get_embeddings
from langchain_community.document_loaders import PyPDFLoader

load_dotenv()

loader = PyPDFLoader("./uploads/57e04107-05d7-49aa-a473-1b9cb88a92de.pdf", extraction_mode="plain")
documents = loader.load()

text_splitter = SemanticChunker(
    embeddings=get_embeddings(),
    # breakpoint_threshold_type="percentile"  # 可选: 调整分块敏感度
)
docs = text_splitter.split_documents(documents)
for doc in docs:
  print(doc.page_content)
  print("=================================")
