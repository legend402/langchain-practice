from typing import Callable
from langchain.messages import ToolMessage
from langchain_classic.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
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
  print(result)
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
  return search_state

@node_hook(after_hook=next_redirect)
def read_node(state: AgentState):
  return create_structure_node(state, reader_prompt, reader_input)

@node_hook(after_hook=next_redirect)
def analyze_node(state: AgentState):
  return create_structure_node(state, analyze_prompt, analyse_input)

@node_hook(after_hook=next_redirect)
def tag_node(state: AgentState):
  return create_structure_node(state, tag_prompt, tag_input)

@node_hook(after_hook=next_redirect)
def knowledge_node(state: AgentState):
  return create_structure_node(state, knowledge_prompt, knowledge_input)

@node_hook()
def reviewer_node(state: AgentState):
  return create_structure_node(state, reviewer_prompt, reviewer_input)

@node_hook()
def human_gate_node(state: AgentState):
  result = create_structure_node(state, human_gate_prompt, human_gate_input)
  print("==================human_gate_node====================")
  feedback = interrupt({
    "human_message": result.get("human_message", ""),
    "expected_reply_schema": result.get("expected_reply_schema", {})
  })
  result["human_feedback"] = feedback
  return result

@node_hook()
def finalize_node(state: AgentState):
  return create_structure_node(state, finalize_prompt, finalize_input)


def route_supervisor_node(state: AgentState):
  """总体路由"""
  return state["next"]

def route_review_node(state: AgentState):
  """审核路由"""
  return state["review_result"]["status"]

def route_human_gate_node(state: AgentState):
  """用户判断应该走哪一条路线"""
  return state["human_feedback"]["decision"]
