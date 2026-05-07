from typing import TypedDict

class WorkflowState(TypedDict):
  input: str
  source_url: str
  source_content: str
  search_query: str
  search_content: str
  summary_content: str
  knowledge_points: list[str]
