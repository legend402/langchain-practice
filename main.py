import asyncio
import os

from RAG import get_chunks
from RAG.milvus import MilvusProcessor
from deepResearch import create_knowledge_agent
from tests import *
# from http_server.rag_server import create_rag_server
from http_server.hig_rag_server import create_high_rag
from tests import  *
from dotenv import load_dotenv

from utils import read_pdf
from utils.rich_print import enable_rich_print

enable_rich_print()

load_dotenv('.env')
app = create_high_rag()
# if __name__ == "__main__":
	# asyncio.run(create_knowledge_agent())
	# create_knowledge_agent()
