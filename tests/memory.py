from models.deepseek import init_deepseek
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage

def memory_test():
	# 初始化大模型
	llm = init_deepseek()
	# 创建智能体
	agent = create_agent(
		model = llm,
		tools = [],
		# 添加记忆模块，使用后，需要为每个输入消息设置唯一的 thread_id, 作为会话窗口id
		checkpointer = InMemorySaver(),
		system_prompt = "你是一个帮助用户的助手, 回答问题简洁，明了，不说废话",
	)
	inputs = {
		"messages": [HumanMessage(content="你好，我是一位前端AI开发")]
  }
	
	for message_chunk, metadata in agent.stream(inputs, config={"configurable": {"thread_id": "123"}}, stream_mode="messages"):
		print(message_chunk.content, end="", flush=True)

	inputs = {
		"messages": [HumanMessage(content="我会做什么")]
  }
	print("\n")
	for message_chunk, metadata in agent.stream(inputs, config={"configurable": {"thread_id": "123"}}, stream_mode="messages"):
		print(message_chunk.content, end="", flush=True)
