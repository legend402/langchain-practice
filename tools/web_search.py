from langchain.tools import tool
from langchain_tavily import TavilyExtract, TavilySearch

@tool
def web_search(query: str, max_results: int = 5):
  """
  提供网络搜索功能

  :param query: 搜索查询。
  :param max_results: 返回的最大结果数。
  :return: 搜索结果列表。
  """
  search = TavilySearch(max_results=max_results)
  results = search.invoke(query)
  return results

@tool
def web_fetch(url: str):
  """
    提供根据url抓取网页的功能

    :parma url: 网页url
    :return: JSON 格式，包含提取的文本、元数据等。
  """
  extract_tool = TavilyExtract()
  result = extract_tool.invoke({"urls": [url]})
  return result