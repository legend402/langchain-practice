from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import tool

@tool
def web_search(query: str, max_results: int = 5):
  """
  提供网络搜索功能

  :param query: 搜索查询。
  :param max_results: 返回的最大结果数。
  :return: 搜索结果列表。
  """
  search = TavilySearchResults(max_results=max_results)
  results = search.invoke(query)
  return results