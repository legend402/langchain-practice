from langgraph.func import END, START
from langgraph.graph import StateGraph

from deepResearch.nodes import *
from deepResearch.state import WorkflowState

def create_knowledge_agent():
  builder = StateGraph(WorkflowState)
  builder.add_node("normalize", create_normalize_node)
  builder.add_node("fetch", create_fetch_node)
  builder.add_node("summary", create_summary_node)

  builder.add_edge(START, "normalize")
  builder.add_edge("fetch", "summary")
  builder.add_conditional_edges("normalize", need_fetch_node, {
    "fetch": "fetch",
    "summary": "summary"
  })

  graph = builder.compile()

  response = graph.invoke({
    "input": "帮我查看一下https://www.runoob.com/ai-agent/langgraph-quick-start.html这个文章讲了什么，并且查询一下langChain的最新版本API使用和文中的用法有什么不同"
  })

  print("===================final_output=======================")
  print(response)