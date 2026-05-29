from typing import Callable

from langchain_classic.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.config import AgentState
from src.llm import init_model
from src.utils import extract_json

async def create_structure_node(state: AgentState, prompt: str, struct_input: Callable[[AgentState], dict]):
    """定义结构化的节点，以便复用"""
    try:
        llm = init_model()
        system_prompt = ChatPromptTemplate([("system", prompt)])
        chain = system_prompt | llm | JsonOutputParser()
        result = await chain.ainvoke(struct_input(state))
    except Exception as e:
        return {"errors": [f"节点执行失败: {str(e)}"], "next": "supervisor"}
    return result

def next_redirect(state: AgentState):
    if state is None:
        return {"next": "supervisor", "errors": ["节点返回了 None"]}
    state["next"] = "supervisor"
    return state
