from abc import abstractmethod
from typing import Any, TypedDict
from langchain.messages import HumanMessage, ToolMessage
from langchain_classic.schema import BaseMessage
from langchain_classic.tools import BaseTool
from langchain_core.language_models import LanguageModelInput
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

class ToolsAgent:
  def __init__(self, llm: ChatOpenAI, tools: list[BaseTool]):
    self._llm_with_tools = llm.bind_tools(tools)
    self._messages: list[BaseMessage] = []
    self._tools_map = {tool.name: tool for tool in tools}
    self._max_loops = 10

  async def ainvoke(self, input: LanguageModelInput, config: RunnableConfig | None = None, **kwargs: Any):
    if isinstance(input, str):
      self._messages.append(HumanMessage(content=input))
    elif isinstance(input, list):
      self._messages.extend(input)
    elif isinstance(input, dict):
      self._messages.extend(input.get("messages", [HumanMessage(content=str(input))]))

    response = await self._llm_with_tools.ainvoke(self._messages)
    self._messages.append(response)
    loops = 0

    while self._messages[-1].tool_calls and loops < self._max_loops:
      for tool_call in self._messages[-1].tool_calls:
        fn = self._tools_map.get(tool_call["name"])
        result = fn.invoke(tool_call["args"]) if fn else f"没有找到名称为{tool_call['name']}的工具"
        self._messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

      response = await self._llm_with_tools.ainvoke(self._messages)
      self._messages.append(response)
      loops += 1
    return [*self._messages]

def create_tools_agent(llm: ChatOpenAI, tools: list[BaseTool] = []):
    return ToolsAgent(llm, tools)
