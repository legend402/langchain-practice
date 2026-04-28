import os

from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from utils.tool_auth_util import *

class SettingConfig:
  def __init__(self, deepseek_api_key: str, amap_api_key: str):
    self.deepseek_api_key = deepseek_api_key
    self.amap_api_key = amap_api_key


def get_setting_config(): 
  """获取env设置配置"""
  deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
  amap_api_key = os.getenv('AMAP_API_KEY')
  return SettingConfig(
    deepseek_api_key,
    amap_api_key
  )

def start_chat(agent: CompiledStateGraph):
  """启动聊天"""
  print('输入 exit 或者 quit 退出')
  while True:
    user_input = input("你:")
    if user_input in { "exit", "quit" }:
      break

    inputs = {
      "messages": [HumanMessage(content=user_input)]
    }

    result = agent.stream(input=inputs, stream_mode="messages", config={"configurable":{ "thread_id": "1" }})

    for chunk, metadata in result:
      print(chunk.content, end="", flush=True)

    print("\n")