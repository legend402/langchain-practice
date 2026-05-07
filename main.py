import asyncio

from rich.console import Console
from deepResearch import create_knowledge_agent
from tests import *
from http_server.rag_server import create_rag_server
from tests import  *
from dotenv import load_dotenv

from utils.rich_print import enable_rich_print

console = Console()
enable_rich_print()

load_dotenv('.env')
app = create_rag_server()

if __name__ == "__main__":
	# asyncio.run(test_browser_search())
	create_knowledge_agent()
