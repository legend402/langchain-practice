from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from tools.get_weather import get_weather_tool
from models.deepseek import init_deepseek
from utils.tool_auth_util import handle_interrupt, prepare_hitl_components
from middleware.BasedToolMiddleware import BasedToolMiddleware

def middleware_test ():
	# 初始化大模型
	llm = init_deepseek()
	# 加载高德mcp工具
	# amap_tools = await McpConfiguration.load_server().get_tools()
	tools = [get_weather_tool]
	# 扫描工具，生成 HITL 中间件配置和元数据映射
	interrupt_on, tool_meta_map = prepare_hitl_components(tools)
	# 创建智能体
	agent = create_agent(
		model = llm,
		tools = tools,
		system_prompt = "你是一个帮助用户的助手, 回答问题简洁，明了，不说废话",
		checkpointer=InMemorySaver(),
		# 自定义中间件
		middleware=[
			HumanInTheLoopMiddleware(
				interrupt_on=interrupt_on
      ),
			BasedToolMiddleware()
    ]
	)
	inputs = {"messages": [HumanMessage("今天杭州天气怎么样")]}
	config = { "configurable": { "thread_id": "1" } }

	result = agent.invoke(inputs, config)

  # 处理中断（循环处理，因为一次恢复后可能再次中断）
	while "__interrupt__" in result:
		result = handle_interrupt(result, agent, config, tool_meta_map)

	for chunk in result["messages"]:
		print(chunk.content)
