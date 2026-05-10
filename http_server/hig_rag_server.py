import json
import os
import uuid

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from pydantic import BaseModel

from RAG.milvus import MilvusProcessor
from http_server.database import UploadRecord, create_mysql_engine, get_session_factory, init_db
from models.deepseek import init_deepseek
from utils import read_pdf

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


def create_high_rag():
    """创建 RAG 服务应用，接入 MySQL 存储上传记录"""
    app = FastAPI()
    milvus = MilvusProcessor("milvus_rag")
    if not milvus.client.has_collection("default"):
       milvus.create_collection("default")

    engine = create_mysql_engine()
    init_db(engine)
    SessionLocal = get_session_factory(engine)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/upload")
    def upload(file: UploadFile = File(...), name: str = None):
        """上传 PDF 文件，解析文本存入 Milvus，文件存本地，记录存 MySQL"""

        file.file.seek(0)
        file_data = file.file.read()

        filename = name or file.filename
        ext = os.path.splitext(file.filename)[1]
        saved_name = f"{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, saved_name)
        with open(file_path, "wb") as f:
            f.write(file_data)

        session = SessionLocal()
        try:
            record = UploadRecord(
                id=str(uuid.uuid4()),
                filename=filename,
                file_path=file_path,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            result = {
                "id": record.id,
                "filename": record.filename,
                "file_path": record.file_path,
                "created_at": str(record.created_at),
            }
        finally:
            session.close()

        return {"message": "上传成功", "data": result}

    class ChatBody(BaseModel):
      question: str

    @app.post('/chat')
    async def start_chat(item: ChatBody):
      # 加载faiss数据库
      # 将数据转化为LangChain检索工具
      llm = init_deepseek()

      agent = create_agent(
        model=llm,
        tools=[milvus.query_search_tool("default")],
        system_prompt="""你是AI助手，请根据提供的上下文回答问题，确保提供所有细节，如果答案不在上下文中，请说"答案不在上下文中"，不要提供错误的答案""",
      )

      async def event_generator():
        async for event in agent.astream_events({"messages": [HumanMessage(item.question)]}, version="v2"):
          if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
              print(chunk.content, end="", flush=True)
              yield f"data: {json.dumps({"token": chunk.content})}\n\n"
      return StreamingResponse(event_generator(), media_type="text/events-stream")

    @app.post("/embedding/file")
    def embedding_file(file_id: str):
      session = SessionLocal()
      try:
        record = session.query(UploadRecord).filter(UploadRecord.id == file_id).first()
        if not record:
           return {"message": "记录不存在"}
        pdf_text = read_pdf(record.file_path)
        milvus.insert_text("default", pdf_text)
        return {"message": f"文件[{record.filename}]已向量化"}
      except:
        return {"message":"error"}
      finally:
        session.close()

    @app.get("/embedding/query")
    def embedding_query(question: str):
      result = milvus.query_search("default", question)
      return {
        "message": "查询成功",
        "data": result,
      }

    @app.get("/uploads")
    def list_uploads():
        """查询所有上传记录"""
        session = SessionLocal()
        try:
            records = session.query(UploadRecord).all()
            return [
                {
                    "id": r.id,
                    "filename": r.filename,
                    "file_path": r.file_path,
                    "created_at": str(r.created_at),
                }
                for r in records
            ]
        finally:
            session.close()

    return app
