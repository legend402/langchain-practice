import os
from langchain_openai import ChatOpenAI

def init_deepseek_model():
  llm = ChatOpenAI(
    base_url = 'https://api.deepseek.com',
    model = 'deepseek-v4-flash',
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    stream_usage = True,
    streaming = True,
    extra_body = {
      "thinking": {"type": "disabled"},
      "max_tokens": 100000,
    }
  )
  return llm
