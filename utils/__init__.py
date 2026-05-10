import os

from PyPDF2 import PdfReader
from langchain.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from utils.tool_auth_util import *

class SettingConfig:
  def __init__(
    self, 
    deepseek_api_key: str, 
    amap_api_key: str, 
    glm_api_key: str,
    pgsql_db_uri: str,
    mysql_db_uri: str,
  ):
    self.deepseek_api_key = deepseek_api_key
    self.amap_api_key = amap_api_key
    self.glm_api_key = glm_api_key
    self.pgsql_db_uri = pgsql_db_uri
    self.mysql_db_uri = mysql_db_uri


def get_setting_config(): 
  """获取env设置配置"""
  deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
  amap_api_key = os.getenv('AMAP_API_KEY')
  glm_api_key = os.getenv('GLM_API_KEY')
  pgsql_db_uri = os.getenv('PGSQL_DB_URI')
  mysql_db_uri = os.getenv('MYSQL_DB_URI')
  return SettingConfig(
    deepseek_api_key,
    amap_api_key,
    glm_api_key,
    pgsql_db_uri,
    mysql_db_uri,
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

def read_pdf(pdf_doc):
  """读取PDF文件，支持 UploadFile、文件路径(str/Path) 和文件对象"""
  import pathlib
  text = ""
  if isinstance(pdf_doc, (str, pathlib.Path)):
    pdf_reader = PdfReader(str(pdf_doc))
    for page in pdf_reader.pages:
      text += page.extract_text()
  elif hasattr(pdf_doc, 'file'):
    pdf_reader = PdfReader(pdf_doc.file)
    for page in pdf_reader.pages:
      text += page.extract_text()
  elif hasattr(pdf_doc, 'read'):
    pdf_reader = PdfReader(pdf_doc)
    for page in pdf_reader.pages:
      text += page.extract_text()
  return text

def str_to_number(num_str):
    try:
        if "." in num_str:
            return float(num_str)  # 转换为浮点数
        return int(num_str)       # 转换为整数
    except ValueError:
        return None  # 无法转换
