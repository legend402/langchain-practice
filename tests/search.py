
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from mcps.config_loader import McpConfiguration
from models.deepseek import init_deepseek
from utils import start_chat

async def test_browser_search():
  llm = init_deepseek()
  tools = []
  playwrightTools = await McpConfiguration.load_target_mcp("playwright").get_tools()
  print(f"Playwright tools: {[tool.name for tool in playwrightTools]}")
  tools.extend(playwrightTools)
  
  agent = create_agent(
		model = llm,
		tools = tools,
		# 添加记忆模块，使用后，需要为每个输入消息设置唯一的 thread_id, 作为会话窗口id
		checkpointer = InMemorySaver(),
		system_prompt = "你是一个帮助用户的助手, 回答问题简洁，明了，不说废话",
	)
  
  start_chat(agent)
