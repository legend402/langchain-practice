from langgraph.func import END, START
from langgraph.graph import StateGraph

from deepResearch.nodes import *
from deepResearch.state import WorkflowState

def create_knowledge_agent():
  builder = StateGraph(WorkflowState)
  builder.add_node("normalize", create_normalize_node)
  builder.add_node("fetch", create_fetch_node)
  builder.add_node("summary", create_summary_node)
  builder.add_node("points", create_knowledge_point_node)
  builder.add_node("knowledges", create_knowledges_node)
  builder.add_node("final", final_node)

  builder.add_edge(START, "normalize")
  builder.add_edge("fetch", "summary")
  builder.add_edge("summary", "points")
  builder.add_edge("summary", "knowledges")
  builder.add_edge("knowledges", "final")
  builder.add_edge("points", "final")
  builder.add_edge("final", END)

  builder.add_conditional_edges("normalize", need_fetch_node, {
    "fetch": "fetch",
    "summary": "summary"
  })

  graph = builder.compile()

  response = graph.invoke({
    "input": "帮我查看一下https://www.runoob.com/ai-agent/langgraph-quick-start.html这个文章讲了什么，并且查询一下langChain的最新版本API使用和文中的用法有什么不同"
  })

  print("===================final_output=======================")
  print(f"内容总结：{response["summary_content"]}")
  print(f"知识标签：{response["knowledges"]}")
  print(f"知识点：{response["knowledge_points"]}")
