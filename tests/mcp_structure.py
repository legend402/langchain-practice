from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from mcps.config_loader import McpConfiguration
from langchain.agents.structured_output import AutoStrategy
from typing import Union
from structured import DistanceResult, RoutePlanResult, DefaultResult
from models.deepseek import init_deepseek

async def mcp_structure_test ():
	# 初始化大模型
	llm = init_deepseek()
	# 加载高德mcp工具
	amap_tools = await McpConfiguration.load_target_mcp("amap-maps").get_tools()
	tools = [*amap_tools]

	# 创建智能体
	agent = create_agent(
		model = llm,
		tools = tools,
		system_prompt = "你是一个帮助用户的助手, 回答问题简洁，明了，不说废话",
		# 自定义结构化输出
		response_format = AutoStrategy(Union[DistanceResult, RoutePlanResult, DefaultResult])
	)
	inputs = {"messages": [HumanMessage("今天杭州天气怎么样")]}
	# for chunk in agent.stream(inputs, stream_mode="values"):
	# 	print(chunk["messages"][-1].pretty_print())

	# 在智能体需要多次调用的情况下，需要ainvoke异步处理
	result = await agent.ainvoke(inputs)
	for chunk in result["messages"]:
		print(chunk.pretty_print())
