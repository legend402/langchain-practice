from models.deepseek import init_deepseek
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from tools.file_sys import *
from tools.web_search import web_search
from utils import start_chat

def chain_test():
  llm = init_deepseek()


  tools = [read_dir, read_file, is_path_exists, web_search]

	# 创建智能体
  agent = create_agent(
		model = llm,
		tools = tools,
		# 添加记忆模块，使用后，需要为每个输入消息设置唯一的 thread_id, 作为会话窗口id
		checkpointer = InMemorySaver(),
		system_prompt = "你是一个帮助用户的助手, 回答问题简洁，明了，不说废话",
	)

  start_chat(agent)
