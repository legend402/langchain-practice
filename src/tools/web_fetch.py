from langchain.tools import tool
from langchain_tavily import TavilyExtract

@tool
def web_fetch(urls: list[str]):
    """
    提供根据urls批量抓取网页的功能

    :param urls: 由网页url组成的字符数组
    :return: JSON 格式，包含提取的文本、元数据等。
    """
    extract_tool = TavilyExtract()
    result = extract_tool.invoke({"urls": urls})
    return result
