import os

class SettingConfig:
  def __init__(self, deepseek_api_key: str):
    self.deepseek_api_key = deepseek_api_key


def get_setting_config(): 
  """获取env设置配置"""
  deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
  return SettingConfig(
    deepseek_api_key=deepseek_api_key
  )