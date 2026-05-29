import os
from langchain_openai import ChatOpenAI

def init_model(
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    streaming: bool = True,
    max_tokens: int = 100000,
    **kwargs,
):
    return ChatOpenAI(
        base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
        model=model or os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        api_key=api_key or os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY")),
        stream_usage=True,
        streaming=streaming,
        max_tokens=max_tokens,
        extra_body={"thinking": {"type": "disabled"}, "type": "json_object"},
        **kwargs,
    )
