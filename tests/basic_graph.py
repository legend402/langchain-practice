
from typing import Annotated, Callable, Optional, TypedDict
from langchain.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.func import START, END
from langgraph.graph import StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from models.deepseek import init_deepseek
from tools.get_weather import get_weather_tool
from utils import get_setting_config, str_to_number

def basic_graph_calc():
  # 定义结构化状态
  class CalcState(BaseModel):
    x: int

  # 定义节点函数，接受并返回CalcState
  def addition(state: CalcState) -> CalcState:
    return CalcState(x=state.x + 1)

  def subtraction(state: CalcState) -> CalcState:
    return CalcState(x=state.x - 2)

  # 构建图
  builder = StateGraph(CalcState)

  builder.add_node(addition)
  builder.add_node(subtraction)

  builder.add_edge(START, "addition")
  builder.add_edge("addition", "subtraction")
  builder.add_edge("subtraction", END)

  graph = builder.compile()

  # 执行图，传入结构化状态对象
  initial_state = CalcState(x=0)
  final_state = graph.invoke(initial_state)

  print("\n最后结果：->", final_state)

def basic_graph_calc_high():
  class CalcState(BaseModel):
    x: int
    done: Optional[bool] = False

  def check_x(state: CalcState) -> CalcState:
    print(f"[check_x] 当前 x = {state.x}")
    return state

  def is_negative_number(state: CalcState) -> bool:
    print(f"[is_negative_number] 当前 x {"< 0" if state.x < 0 else "> 0"}")
    return state.x < 0
  
  def increment(state: CalcState) -> CalcState:
    num = str_to_number(input("请输入一个数字：").strip())
    return CalcState(x=state.x + num)
  
  def done(state: CalcState) -> CalcState:
    return CalcState(x=state.x, done = True)
  
  builder = StateGraph(CalcState)

  builder.add_node(check_x)
  builder.add_node(increment)
  builder.add_node("done_node", done)

  builder.add_conditional_edges("check_x", is_negative_number, {
    True: "done_node",
    False: "increment"
  })

  builder.add_edge("increment", "check_x")
  
  builder.add_edge(START, "check_x")
  builder.add_edge("done_node", END)

  graph = builder.compile()

  print("\n初始 x=6（正数，进入循环）")
  final_state = graph.invoke(CalcState(x=6))
  print("[最终结果] ->", final_state)

def basic_graph_chat():
  class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

  llm = init_deepseek()
  tools = [get_weather_tool]
  model = llm.bind_tools(tools)

  def call_model(state: AgentState):
    system_prompt = SystemMessage(
      "你是一个AI助手，可以依据用户提问产生回答，你还具备调用天气函数的能力"
    )
    response = model.invoke([system_prompt] + state["messages"])
    return {
      "messages": [response]
    }
  tool_node = ToolNode(tools)

  def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if not last_message.tool_calls:
      return "end"
    else:
      return "continue"
  
  builder = StateGraph(AgentState)

  builder.add_node("agent", call_model)
  builder.add_node("tools", tool_node)

  builder.add_edge(START, "agent")
  builder.add_edge("tools", "agent")
  builder.add_conditional_edges("agent", should_continue, {
    "end": END,
    "continue": "tools"
  })

  graph = builder.compile()

  response = graph.invoke({ "messages": ["查询一下杭州的天气"] })
  print(response["messages"])

def basic_graph_short_memory():
  class MessageState(TypedDict):
    messages: Annotated[list, add_messages]

  model = init_deepseek()

  db_uri = get_setting_config().pgsql_db_uri

  with PostgresSaver.from_conn_string(db_uri) as checkpointer:
    # 第一次调用必须要setup()初始化
    checkpointer.setup()

    def call_model(state: MessageState):
      response = model.invoke([SystemMessage("你是一名智能问答助手，回答问题要简介，明了")] + state["messages"])
      return { "messages": response }
    
    builder = StateGraph(MessageState)
    builder.add_node(call_model)
    builder.add_edge(START, "call_model")

    graph = builder.compile(checkpointer=checkpointer)
    config = {
      "configurable": {
        "thread_id": "1"
      }
    }

    def create_stream_chat(agent: CompiledStateGraph[MessageState, None, MessageState, MessageState], message: str, cb: Callable[[str], None]):
      print(f"{message}\n")
      response = agent.stream({
        "messages": [
          HumanMessage(content=message)
        ],
      }, config, stream_mode="messages")

      for chunk, metadata in response:
        if hasattr(chunk, "content") and chunk.content:
          cb(chunk.content)

    def custom_print(chunk: str):
      print(chunk, end="", flush=True)

    create_stream_chat(graph, "你好，我是一名AI应用开发", custom_print)

    create_stream_chat(graph, "帮我写一个langGraph的基础应用demo代码", custom_print)
