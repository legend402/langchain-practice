import os
from uuid import UUID, uuid4

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.db.db import FileUpload


UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm", ".docx", ".doc", ".pdf"}

def ensure_upload_dir() -> None:
  """
    确保 uploads 目录存在。
  """
  os.makedirs(UPLOAD_DIR, exist_ok=True)

async def upload_file(
  session: AsyncSession,
  user_id: UUID,
  file_name: str,
  file_content: bytes,
) -> FileUpload:
  """
    上传文件到本地磁盘并写入数据库记录。
    参数:
        session: 数据库会话
        user_id: 用户 ID
        file_name: 原始文件名
        file_content: 文件二进制内容
    返回:
        FileUpload 数据库记录
  """
  ensure_upload_dir()
  ext = os.path.splitext(file_name)[1].lower()
  if ext not in ALLOWED_EXTENSIONS:
    raise ValueError(f"不支持的文件格式: {ext}")
  
  file_id = str(uuid4())
  stored_name=f"{file_id}{ext}"
  file_path = os.path.join(UPLOAD_DIR, stored_name)

  with open(file_path, "wb") as f:
    f.write(file_content)

  record = FileUpload(
    id=file_id,
    user_id=user_id,
    file_name=file_name,
    file_path=file_path,
    file_format=ext.lstrip("."),
    file_size=len(file_content)
  )
  session.add(record)
  await session.commit()
  await session.refresh(record)
  return record

async def get_file_record(session: AsyncSession, file_id: str) -> FileUpload | None:
  """
    根据 ID 获取文件上传记录。
    参数:
        session: 数据库会话
        file_id: 文件 ID
    返回:
        FileUpload 记录或 None
  """
  return await session.get(FileUpload, file_id)

async def list_files(
  session: AsyncSession, user_id: UUID,
) -> list[FileUpload]:
  """
    获取用户的文件上传列表。
    参数:
        session: 数据库会话
        user_id: 用户 ID
    返回:
        FileUpload 列表
  """
  result = await session.exec(
    select(FileUpload)
    .where(FileUpload.user_id == user_id)
    .order_by(FileUpload.create_at.desc())
  )
  return result.all()

async def delete_file(session: AsyncSession, file_id: str, user_id: UUID) -> bool:
  """
  删除文件（磁盘文件 + 数据库记录）。
  参数:
      session: 数据库会话
      file_id: 文件 ID
      user_id: 用户 ID
  返回:
      是否删除成功
  """
  record = await session.get(FileUpload, file_id)
  if not record or str(record.user_id) != str(user_id):
      return False
  if os.path.exists(record.file_path):
      os.remove(record.file_path)
  await session.delete(record)
  await session.commit()
  return True
