from pydantic import BaseModel
from src.config import AgentState

_LIST_FIELDS = frozenset({
    "source_materials",
    "search_results",
    "source_index",
    "read_notes",
    "evidence_items",
    "constraints",
    "errors",
    "trace",
})

def merge_state(state: AgentState, update: dict | BaseModel) -> AgentState:
  """
  将 update 字典合并到 state 中。
  列表字段（search_results、read_notes 等）执行追加操作；
  标量/对象字段直接用 update 的值覆盖（跳过 None）；
  iteration_count 执行累加。
  参数:
      state: 当前的 AgentState
      update: 节点返回的增量状态字典
  返回:
      合并后的 AgentState
  """

  if (isinstance(update, BaseModel)):
    items = update.model_dump().items()
  else:
    items = update.items()

  for key, value in items:
    if value is None:
      continue
    if key == "iteration_count":
      state[key] = state.get(key, 0) + value
    elif key in _LIST_FIELDS:
      state.setdefault(key, []).extend(value)
    else:
      state[key] = value
  return state


def get_initial_state(state: AgentState):
  initial_state: AgentState = {
    "messages": [],
    "user_query": "",
    "task_goal": "根据用户问题或资料生成结构化知识点总结",
    "constraints": [],
    "output_preferences": {
        "format": "markdown",
        "language": "zh-CN",
    },

    "source_materials": [],
    "search_results": [],
    "source_index": [],

    "read_notes": [],
    "read_notes_summary": "",
    "evidence_items": [],

    "analysis_result": None,
    "analysis_summary": None,
    "tags": None,
    "knowledge_summary": None,

    "review_result": None,
    "human_feedback": None,

    "final_answer": None,

    "next": None,
    "supervisor_reason": None,
    "iteration_count": 0,
    "max_iterations": 8,
    "errors": [],
    "trace": [],
  }
  new_state = merge_state(initial_state, state)
  if not len(new_state["messages"]):
    new_state["messages"] = [("human", state["user_query"])]
  return new_state

def get_state_message(node_name: str, state: dict) -> str:
  match node_name:
    case "supervisor":
      return f"[supervisor]: {state["supervisor_reason"]}"
    case "search":
      return f"[search]: 搜索完成，找到 {len(state["search_results"])} 篇相关资料"
    case "read":
      return f"[read]: 阅读完成，提取了 {len(state["read_notes"])} 条笔记"
    case "analyze":
      return f"[analyze]: {state["analysis_summary"]}"
    case "tag":
      return f"[tag]: 标签生成完成，提取了{len(state["tags"]["keywords"])}个关键词，提取了{len(state["tags"]["topic"])}个主题标签，提取了{len(state["tags"]["domain"])}个领域标签"
    case "knowledge":
      return f"[knowledge]: 提取了{len(state["knowledge_summary"]["key_points"])}个知识点，总结如下：{state["knowledge_summary"]["summary"]}"
    case "review":
      review_result = state["review_result"]
      review_status = review_result["status"]
      
      suggestions = "没有建议" if len(review_result["suggestions"]) == False else f"建议如下：{",".join(review_result["suggestions"])}"
      issues = "没有问题" if len(review_result["issues"]) == False else f"问题如下：{",".join(review_result["issues"])}"
      return f"[review]: 审核结果为{review_status},{suggestions},{issues}"
    case "human":
      feedback = state["human_feedback"]
      if feedback:
        return f"[AI]: 用户反馈结果：{feedback["decision"]}，给出如下建议: {feedback["comment"]}"
      return f"[human]: {state["human_message"]}"
    case "finalize":
      return f"[finalize]: {state["final_answer"]}"
    case _:
      return ""

def recover_state(messages: list[dict]):
  state: AgentState = {
    "messages": []
  }
  for message in messages:
    if message.role == "human":
      state["user_query"] = message.content
    else:
      node_state = message.state
      if not node_state: continue
      del node_state["session_id"]
      node_name = list(node_state.keys())[0]
      node_state = node_state.get(node_name, {})
      state = {
        **state,
        **node_state,
        "messages": state["messages"] + [("AI", get_state_message(node_name, node_state))]
      }
  return state    
