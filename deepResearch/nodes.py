from langchain.agents import create_agent
from langchain.messages import HumanMessage
from pydantic import BaseModel, Field
from deepResearch.state import WorkflowState
from models.deepseek import init_deepseek
from tools.web_search import web_search, web_fetch

def create_normalize_node(state: WorkflowState):
  llm = init_deepseek()

  class DefaultResult(BaseModel):
    """ normalize_node """
    source_url: str = Field(description="需要提取内容的网址")
    search_query: str = Field(description="联网搜索关键字")

  sys_prompt = (
    "你是一名内容整理员，要将用户的输入内容整理"
    "查看是否有需要提取内容的网址，是否需要联网搜索的内容，有的话整理成一些关键字方便搜索"
  )

  agent = create_agent(
    model=llm,
    system_prompt=sys_prompt,
    response_format=DefaultResult
  )

  response = agent.invoke({
    "messages": [HumanMessage(content=state["input"])]
  })
  struct_res = response["structured_response"]
  print("===================create_normalize_node=======================")
  print(struct_res)
  
  return {
    "source_url": struct_res.source_url or "",
    "search_query": struct_res.search_query or "",
  }

def need_fetch_node(state: WorkflowState):
  if state["source_url"] or state["search_query"]:
    return "fetch"
  else:
    return "summary"

def create_fetch_node(state: WorkflowState):
  llm = init_deepseek()

  class DefaultResult(BaseModel):
    """ fetch_node """
    source_content: str = Field(description="精炼后的网址内容")
    search_content: str = Field(description="精炼后的查询内容")

  sys_prompt=(
    "你是一个查询网页的专员，会查询网页获取信息或者拉取网页内容读取信息，并且分别总结精炼内容"
  )

  tools = [web_search, web_fetch]

  agent = create_agent(
    model=llm,
    system_prompt=sys_prompt,
    tools=tools,
    response_format=DefaultResult
  )

  response = agent.invoke({
    "messages": [
      HumanMessage(content=f"这是我要抓取的页面地址: {state["source_url"]}"),
      HumanMessage(content=f"这是我要搜索的内容: {state["search_query"]}"),
    ]
  })
  struct_res = response["structured_response"]
  print("===================create_fetch_node=======================")
  print(struct_res)

  return {
    "source_content": struct_res.source_content or "",
    "search_content": struct_res.search_content or "",
  }

def create_summary_node(state: WorkflowState):
  llm = init_deepseek()

  sys_prompt=(
    "你是一个内容汇总和整理人员，需要把用户的提问需求和抓取的页面和搜索结果进行汇总整理，最后输出"
  )

  agent = create_agent(
    model=llm,
    system_prompt=sys_prompt,
  )
  human_message = state["input"]
  if state["source_url"]:
    human_message += f"\n这是用户提供网站抓取的内容: {state["source_content"]}"
  if state["search_query"]:
    human_message += f"\n这是搜索到的结果: {state["search_content"]}"

  response = agent.invoke({
    "messages": [
      HumanMessage(content=human_message),
    ]
  })
  content = response["messages"][-1].content
  print("===================create_summary_node=======================")
  print(content)

  return {
    "summary_content": content,
  }
