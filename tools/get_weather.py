import json
import os
from api.AMap import get_weather
from decorators.tool_auth import tool_auth

@tool_auth(
  prompt="是否可以获取 '{city_name}' 的天气？(yes/no):",
  decisions=["yes", "no"]
)
def get_weather_tool(city_name: str):
  """为一个城市获取天气信息"""
  city_code = get_city_code(city_name)
  return get_weather(city_code)

def get_city_code (city_name: str):
  # 获取当前脚本所在目录
  current_dir = os.path.dirname(os.path.abspath(__file__))
  # 构建 JSON 文件的绝对路径
  json_path = os.path.join(current_dir, '../json/AMap_adcode_citycode.json')
  # 打开 JSON 文件
  with open(json_path, 'r', encoding='utf-8') as f:
    city_data = json.load(f)
    for city in city_data:
      if city_name in city['name']:
        return city['adcode']
  return None