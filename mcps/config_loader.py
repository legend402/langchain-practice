from langchain_mcp_adapters.client import MultiServerMCPClient
from utils import get_setting_config
import os
import json
import pydash

class McpConfiguration:
  """
    MCP配置类
  """
  @staticmethod
  def load_config(file_path = "servers_config.json"):
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建 JSON 文件的绝对路径
    json_path = os.path.join(current_dir, f'../{file_path}')
    with open(json_path, "r") as f:
      return json.load(f).get("mcpServers", {})
    
  @staticmethod
  def load_server():
    servers = McpConfiguration.load_config()
    return MultiServerMCPClient(servers)

  @staticmethod
  def load_target_mcp(mcp_name: str | list[str]):
    servers = McpConfiguration.load_config()
    mcp_config = pydash.pick(servers, mcp_name if isinstance(mcp_name, list) else [mcp_name])
    print(mcp_config)
    return MultiServerMCPClient(mcp_config)