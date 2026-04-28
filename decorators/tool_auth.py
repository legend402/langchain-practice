from langchain.tools import tool
from functools import wraps

def tool_auth(prompt: str, decisions: list = None):
  """
  装饰器：标记工具需要人工确认，并定义确认提示模板。

  Args:
      prompt: 提示模板，支持 {参数名} 占位符，
                                例如 "是否获取 '{city_name}' 的天气？(approve/reject):"
      decisions: 允许的决策类型，默认为 ["approve", "reject", "edit"]
  """
  decisions = decisions or ["approve", "reject", "edit"]

  def decorator(func):
    wrapper = tool(func)

    metadata = {
      "prompt": prompt,
      "decisions": decisions
    }
    wrapper._tool_auth_meta  = metadata
    return wrapper
  return decorator