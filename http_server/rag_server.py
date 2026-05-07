
import json
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_community.vectorstores import FAISS
from langchain_core.tools import create_retriever_tool
from pydantic import BaseModel

from RAG import check_database_exists, get_chunks, init_embedding_model, vector_store
from models.deepseek import init_deepseek
from utils import read_pdf

def create_rag_server():
  app = FastAPI()
  # 配置 CORS 中间件
  app.add_middleware(
      CORSMiddleware,
      allow_origins=[
          "http://127.0.0.1",
          "http://127.0.0.1:4030",
          "http://127.0.0.1:5500",
          "http://127.0.0.1:8080",
          "http://localhost:5173",
      ],
      allow_credentials=True,       # 允许携带 Cookie
      allow_methods=["*"],          # 允许的 HTTP 方法
      allow_headers=["*"],          # 允许的请求头
  )
  @app.get("/")
  async def root():
    return {"message": "Hello World"}

  @app.post("/uploadPdf")
  async def upload_file(file: UploadFile = File(...)):
    try:
      raw_text = await read_pdf(file if isinstance(file, list) else [file])
    
      if not raw_text.strip():
        return {"message": "文件内容为空", "code": 400}
      print('=========文件内容不为空===========')
      text_chunks = get_chunks(raw_text)
      print(f'=========文本块数量：{len(text_chunks)}===========')
      vector_store(text_chunks)

      return {"message": "文件上传成功", "code": 200}
    except Exception as e:
      return {"message": str(e), "code": 500}

  class ChatBody(BaseModel):
    question: str

  @app.post('/chat')
  async def start_chat(item: ChatBody):
    if not check_database_exists():
      return {"message": "数据库不存在", "code": 400}

    embeddings = init_embedding_model()
    # 加载faiss数据库
    faiss_db = FAISS.load_local("faiss_db", embeddings, allow_dangerous_deserialization=True)
    # 将数据转化为LangChain检索工具
    retriever = faiss_db.as_retriever()
    retriever_tool = create_retriever_tool(retriever, "pdf_extractor", "此工具用于对来自 PDF 文件中的查询内容作出回答。")
    llm = init_deepseek()

    agent = create_agent(
      model=llm,
      tools=[retriever_tool],
      system_prompt="""你是AI助手，请根据提供的上下文回答问题，确保提供所有细节，如果答案不在上下文中，请说"答案不在上下文中"，不要提供错误的答案""",
    )

    async def event_generator():
      async for event in agent.astream_events({"messages": [HumanMessage(item.question)]}, version="v2"):
        if event["event"] == "on_chat_model_stream":
          chunk = event["data"]["chunk"]
          if chunk.content:
            yield f"data: {json.dumps({"token": chunk.content})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/events-stream")

  @app.get("/checkDb")
  def check_db():
    return {
      "code": 200 if check_database_exists() else 400,
    }
  
  return app
