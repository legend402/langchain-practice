import os
from langchain_openai import ChatOpenAI

def init_glm_model():
  """初始化glm模型"""
  # 获取env配置
  glm_coding_url="https://api.z.ai/api/coding/paas/v4"

  llm = ChatOpenAI(
      base_url = glm_coding_url,
      model = 'glm-4.6v',
      api_key = os.getenv('GLM_EN_API_KEY'),
      stream_usage = True,
      streaming = True,
  )
  return llm
