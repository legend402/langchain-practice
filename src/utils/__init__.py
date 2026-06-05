import json, re
import time
import inspect
from typing import Callable, Optional

from langchain.messages import HumanMessage
from pydantic import BaseModel

from src.config import AgentState
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

Hook = Callable[[AgentState], Optional[AgentState]]

def node_hook(before_hook: Optional[Hook] = None, after_hook: Optional[Hook] = None):
  def decorator(func):
    is_async = inspect.iscoroutinefunction(func)

    async def _run(state: AgentState):
      if before_hook is not None:
        before_state = before_hook(state)
        if before_state is not None:
          state = before_state

      if is_async:
        new_state = await func(state)
      else:
        new_state = func(state)

      if after_hook is not None:
        after_state = after_hook(new_state)
        if after_state is not None:
          new_state = after_state
      return new_state

    async def wrapper(state: AgentState):
      return await _run(state)

    return wrapper
  return decorator
