from typing import Dict
from langgraph.types import Command

# ------------------------------
# 扫描工具，生成 HITL 配置和元数据映射
# ------------------------------
def prepare_hitl_components(tools: list):
  """
    根据工具的 _tool_auth_meta 元数据，同时生成：
    - interrupt_on 配置（用于 HumanInTheLoopMiddleware）
    - tool_meta_map（用于中断处理函数动态生成提示）
  """
  interrupt_on = {}
  tool_meta_map = {}
  for tool in tools:
    meta = getattr(tool, '_tool_auth_meta', None)
    if meta:
      name = tool.name
      interrupt_on[name] = {"allowed_decisions": ["approve", "reject", "edit"]}
      tool_meta_map[name] = meta
  return interrupt_on, tool_meta_map

# ------------------------------
# 统一的中断处理函数（同步控制台版本）
# ------------------------------
def handle_interrupt(result: Dict, agent, config: Dict, tool_meta_map: Dict):
  """
    处理 __interrupt__，根据工具元数据向用户询问决策，并恢复执行。
    返回最终 Agent 状态。
  """
  if "__interrupt__" not in result:
    return result
  
  interrupt_value = result["__interrupt__"][0].value
  action_requests = interrupt_value["action_requests"]
  decisions = []

  for action in action_requests:
    tool_name = action["name"]
    tool_args = action["args"]
    meta = tool_meta_map.get(tool_name, {})
    template = meta.get("prompt")
    meta_decisions = meta.get("decisions")

    if template:
      try:
        prompt = template.format(**tool_args)
      except KeyError as e:
        print(e)
        prompt = f"工具 '{tool_name}' 请求确认（参数：{tool_args}），是否批准？(approve/reject): "
    else:
      prompt = f"是否允许执行工具 '{tool_name}'？(approve/reject): "

    user_input = input(prompt).strip().lower()
    if user_input == meta_decisions[0]:
      decisions.append({ "type": "approve" })
    else:
      decisions.append({ "type": "reject", "message": "用户拒绝执行" })

  return agent.invoke(Command(resume={ "decisions": decisions }), config)
