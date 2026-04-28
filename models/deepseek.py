
from langchain_openai import ChatOpenAI
from utils import get_setting_config

def init_deepseek():
  """初始化DeepSeek模型"""
  # 获取env配置
  config = get_setting_config()

  llm = ChatOpenAI(
      base_url = 'https://api.deepseek.com',
      model = 'deepseek-v4-flash',
      api_key = config.deepseek_api_key,
      stream_usage = True,
      streaming = True,
      extra_body = {
        "thinking": {"type": "disabled"}
      }
  )
  return llm