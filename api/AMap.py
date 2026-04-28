import requests
from utils import get_setting_config


def get_weather(city_code: str):
  """为一个城市获取天气信息"""
  # 获取env配置
  config = get_setting_config()
  AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

  response = requests.get(AMAP_WEATHER_URL, {
    "key": config.amap_api_key,
    "city": city_code,
    "extensions": "base"
  })

  return response.text

class Location:
  def __init__(self, longitude: str, latitude: str):
    self.longitude = longitude
    self.latitude = latitude

def get_posi_by_address(address: str):
  """根据地址获取位置信息"""
  AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

  response = requests.get(AMAP_GEOCODE_URL, {
    "key": config.amap_api_key,
    "address": address
  })
  parse = response.json()
  if parse['status'] == '1':
    location = parse['geocodes'][0]['location']
    longitude, latitude = location.split(",")
    return Location(longitude, latitude)
  return None
