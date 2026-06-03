from langchain_community.tools import tool


@tool
async def read_file(file_id: str) -> str:
  """
  文件读取工具。根据 file_id 读取用户上传的文件内容。
  当用户在聊天中上传附件时，必须先调用此工具获取文件内容。
  :file_id str: 文件上传后返回的文件 ID
  """
  from src.service.db.database import engine
  from sqlmodel.ext.asyncio.session import AsyncSession
  from src.service.controller.FileUpload import get_file_record
  from src.utils.reader import read

  async with AsyncSession(engine) as session:
      record = await get_file_record(session, file_id)
      if not record:
          return f"未找到文件: {file_id}"
      try:
          text = read(record.file_path)
          return text
      except Exception as e:
          return f"文件读取失败: {str(e)}"