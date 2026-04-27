from langchain_mcp_adapters.client import MultiServerMCPClient
from api.AMap import AMAP_WEATHER_API_KEY

def init_amap_mcp ():
  # 初始化高德地图MCP客户端
  return MultiServerMCPClient(
    {
      "amap-maps": {
        "command": "cmd",
        "args": [
          "/c",
          "npx",
          "-y",
          "@amap/amap-maps-mcp-server"
        ],
        "env": {
          "AMAP_MAPS_API_KEY": AMAP_WEATHER_API_KEY
        },
        'transport': 'stdio'
      }
    }
  )