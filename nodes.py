from typing import Callable
from langchain.messages import SystemMessage
from langchain_classic.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph.ui import get_stream_writer
from langgraph.types import interrupt
from agent.create_tools_agent import create_tools_agent
from config import AgentState
from llm import init_deepseek_model
from prompt import *
from tools import web_fetch, web_search
from utils import extract_json, node_hook

def create_structure_node(state: AgentState, prompt: str, struct_input: Callable[[AgentState], dict]):
  """定义结构化的节点，以便复用"""
  try:
    llm = init_deepseek_model()
    system_prompt = ChatPromptTemplate([
      ("system", prompt)
    ])
    chain = system_prompt | llm | JsonOutputParser()
    result = chain.invoke(struct_input(state))
  except Exception as e:
    return {"errors": [f"节点执行失败: {str(e)}"], "next": "supervisor"}

  return result

def next_redirect(state: AgentState):
  if state is None:
    return { "next": "supervisor", "errors": ["节点返回了 None"] }
  state["next"] = "supervisor"
  return state

@node_hook()
def supervisor_node(state: AgentState):
  llm = init_deepseek_model()
  system_prompt = ChatPromptTemplate.from_messages([
    ("system", supervisor_prompt),
  ])

  supervisor_chain = system_prompt | llm | JsonOutputParser()
  result = supervisor_chain.invoke(supervisor_input(state))
  result = _validate_supervisor_result(result, state)
  
  messages = state["messages"] + [("AI", f"[supervisor]: {result["supervisor_reason"]}")]
  result["messages"] = messages
  return result

def _validate_supervisor_result(result: dict, state: AgentState) -> dict:
  next_val = result.get("next", "")
  reason = result.get("supervisor_reason", "")

  review_result = state.get("review_result")
  human_feedback = state.get("human_feedback")
  has_knowledge_summary = bool(state.get("knowledge_summary"))

  if next_val == "finalize":
    review_passed = (
      isinstance(review_result, dict)
      and review_result.get("status") == "pass"
    )
    human_approved = (
      isinstance(human_feedback, dict)
      and human_feedback.get("decision") == "approved"
    )
    if not review_passed and not human_approved:
      corrected = "review" if has_knowledge_summary else "knowledge"
      result["next"] = corrected
      result["supervisor_reason"] = (
        f"[自动修正] 原因: finalize 未通过校验（review_result={review_result}, "
        f"human_feedback={human_feedback}），已修正为 {corrected}。原始原因: {reason}"
      )
  return result

@node_hook(after_hook=next_redirect)
def search_node(state: AgentState):
  llm = init_deepseek_model()
  messages = ChatPromptTemplate.from_messages([
    ("system", search_prompt)
  ]).format_messages(**searcher_input(state))

  llm_with_tools = create_tools_agent(llm=llm, tools=[web_search, web_fetch])
  response = llm_with_tools.invoke(messages)

  search_state = extract_json(response[-1].content)
  if search_state is None:
    return {
      "errors": ["search流程获取数据异常"]
    }
    
  search_state["messages"] = state["messages"] + [("AI", f"[search]: 搜索完成，找到 {len(search_state["search_results"])} 篇相关资料")]
  return search_state

@node_hook(after_hook=next_redirect)
def read_node(state: AgentState):
  result = create_structure_node(state, reader_prompt, reader_input)
  result["messages"] = [("AI", f"[read]: 阅读完成，提取了 {len(result["read_notes"])} 条笔记")]
  return result

@node_hook(after_hook=next_redirect)
def analyze_node(state: AgentState):
  result = create_structure_node(state, analyze_prompt, analyse_input)
  result["messages"] = state["messages"] + [("AI", f"[analyze]: {result["analysis_summary"]}")]
  return result

@node_hook(after_hook=next_redirect)
def tag_node(state: AgentState):
  result = create_structure_node(state, tag_prompt, tag_input)
  result["messages"] = state["messages"] + [("AI", f"[tag]: 标签生成完成，提取了{len(result["tags"]["keywords"])}个关键词，提取了{len(result["tags"]["topic"])}个主题标签，提取了{len(result["tags"]["domain"])}个领域标签")]
  return result

@node_hook(after_hook=next_redirect)
def knowledge_node(state: AgentState):
  result = create_structure_node(state, knowledge_prompt, knowledge_input)
  result["messages"] = state["messages"] + [("AI", f"[knowledge]: 提取了{len(result["knowledge_summary"]["key_points"])}个知识点，总结如下：{result["knowledge_summary"]["summary"]}")]
  return result

@node_hook()
def reviewer_node(state: AgentState):
  result = create_structure_node(state, reviewer_prompt, reviewer_input)
  
  review_result = result["review_result"]
  review_status = review_result["status"]
  
  suggestions = "没有建议" if len(review_result["suggestions"]) == False else f"建议如下：{",".join(review_result["suggestions"])}"
  issues = "没有问题" if len(review_result["issues"]) == False else f"问题如下：{",".join(review_result["issues"])}"
  
  result["messages"] = state["messages"] + [("AI", f"[review]: 审核结果为{review_status},{suggestions},{issues}")]
  return result

@node_hook()
def human_gate_node(state: AgentState):
  result = create_structure_node(state, human_gate_prompt, human_gate_input)
  result["messages"] = state["messages"] + [("AI", f"[human]: {result["human_message"]}")]
  print("==================human_gate_node====================")
  feedback = interrupt({
    "human_message": result.get("human_message", ""),
    "expected_reply_schema": result.get("expected_reply_schema", {})
  })
  result["human_feedback"] = feedback
  result["messages"].append(("human", f"[human]: 用户反馈结果：{feedback["decision"]}，给出如下建议: {feedback["comment"]}"))
  return result

@node_hook()
async def finalize_node(state: AgentState):
  # result = create_structure_node(state, finalize_prompt, finalize_input)
  llm = init_deepseek_model()
  writer = get_stream_writer()
  messages = [
    SystemMessage(content=finalize_prompt.format(**finalize_input(state))),
  ]
  full_text = ""
  async for chunk in llm.astream(messages):
    if chunk.content:
      full_text += chunk.content
      writer({ "stream_chunk": { "chunk": chunk.content, "node_output_key": "finalize" } })

  return {
    "final_answer": full_text,
    "trace": ["finalize completed"],
    "messages": state["messages"] + [("AI", f"[finalize]: {full_text}")]
  }

def route_supervisor_node(state: AgentState):
  """总体路由"""
  return state["next"]

def route_review_node(state: AgentState):
  """审核路由"""
  return state["review_result"]["status"]

def route_human_gate_node(state: AgentState):
  """用户判断应该走哪一条路线"""
  return state["human_feedback"]["decision"]
