from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from RAG import check_database_exists, get_chunks, vector_store
from utils import read_pdf
app = FastAPI()
# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1",
        "http://127.0.0.1:4030",
    ],
    allow_credentials=True,       # 允许携带 Cookie
    allow_methods=["*"],          # 允许的 HTTP 方法
    allow_headers=["*"],          # 允许的请求头
)
@app.get("/")
async def root():
  return {"message": "Hello World"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
  try:
    raw_text = await read_pdf(file if isinstance(file, list) else [file])
  
    if not raw_text.strip():
      return {"message": "文件内容为空", "code": 400}
    print('=========文件内容不为空===========')
    if not check_database_exists():
      return {"message": "数据库不存在", "code": 400}
    print('=========数据库存在===========')
    text_chunks = get_chunks(raw_text)
    print(f'=========文本块数量：{len(text_chunks)}===========')
    vector_store(text_chunks)

    return {"message": "文件上传成功", "code": 200}
  except Exception as e:
    return {"message": str(e), "code": 500}