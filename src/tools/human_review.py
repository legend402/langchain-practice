from langchain_core.tools import tool

@tool
def request_human_review(reason: str):
    """当需要人工判断或存在多种选择需要用户抉择时调用此工具。
    reason: 需要人工干预的详细原因
    """
    pass  # 工具本身不做实际逻辑，只是作为信号