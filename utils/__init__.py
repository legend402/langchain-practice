import json, re
import time
from typing import Callable, Optional

from pydantic import BaseModel

from config import AgentState
def extract_json(text: str) -> dict:
  try:
    return json.loads(text)
  except json.JSONDecodeError:
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
      return json.loads(match.group(1))
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
      return json.loads(match.group())
    raise

type Hook= Callable[[AgentState], Optional[AgentState]]

def node_hook(before_hook: Optional[Hook] = None, after_hook: Optional[Hook] = None):
  def decorator(func):
    def wrapper(state: AgentState):
      if before_hook is not None:
        before_state = before_hook(state)
        if before_state is not None:
          state = before_state

      # start = time.perf_counter()
      # print(f"开始执行{state["next"]}任务节点")
      new_state = func(state)
      # print(f"{state["next"]}任务节点执行完毕，节点用时: {time.perf_counter() - start:.3f}s")

      if after_hook is not None:
        after_state = after_hook(new_state)
        if after_state is not None:
          new_state = after_state
      return new_state
    return wrapper
  return decorator

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
  print(new_state)
  return new_state
