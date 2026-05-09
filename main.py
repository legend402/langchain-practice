import asyncio
import os

from RAG import get_chunks
from RAG.milvus import MilvusProcessor
from deepResearch import create_knowledge_agent
from tests import *
# from http_server.rag_server import create_rag_server
from tests import  *
from dotenv import load_dotenv

from utils import read_pdf
from utils.rich_print import enable_rich_print

enable_rich_print()

load_dotenv('.env')
# app = create_rag_server()
async def main():
	milvus = MilvusProcessor(database="test")
	current_dir = os.path.dirname(os.path.abspath(__file__))
  # 构建 JSON 文件的绝对路径
	json_path = os.path.join(current_dir, './docs/DeepSeek-R1高性能部署实战.pdf')
	print("----------------------------")
	pdf_text = read_pdf(json_path)
	print("--------------create_collection--------------")
	milvus.create_collection("deepseek")
	print("-------------insert_text---------------")
	milvus.insert_text("deepseek", pdf_text)
	print("-------------query_search---------------")
	result = milvus.query_search("deepseek", "Quick Transformers")
	print(result)
if __name__ == "__main__":
	asyncio.run(main())
	# create_knowledge_agent()
