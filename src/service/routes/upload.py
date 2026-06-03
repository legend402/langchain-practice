import os

from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.auth.deps import CurrentUser
from src.service.controller.FileUpload import (
    upload_file,
    list_files,
    get_file_record,
    delete_file,
)
from src.service.db.database import get_session
from src.service.result import Result
from src.utils.reader import read

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/file")
async def upload_file_route(
    user: CurrentUser,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    上传文件到服务器。
    """
    content = await file.read()
    record = await upload_file(session, user.id, file.filename or "unknown.txt", content)
    return Result.success({
        "id": record.id,
        "file_name": record.file_name,
        "file_format": record.file_format,
        "file_size": record.file_size,
        "create_at": str(record.create_at),
    })


@router.get("/files")
async def list_files_route(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    获取当前用户的文件列表。
    """
    files = await list_files(session, user.id)
    return Result.success([
        {
            "id": f.id,
            "file_name": f.file_name,
            "file_format": f.file_format,
            "file_size": f.file_size,
            "create_at": str(f.create_at),
        }
        for f in files
    ])


@router.get("/files/{file_id}/content")
async def get_file_content_route(
    file_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    根据 file_id 获取文件文本内容。
    """
    record = await get_file_record(session, file_id)
    if not record or str(record.user_id) != str(user.id):
        return Result.error("文件不存在")
    try:
        text = read(record.file_path)
        return Result.success({"text": text})
    except Exception as e:
        return Result.error(f"文件读取失败: {str(e)}")


@router.delete("/files/{file_id}")
async def delete_file_route(
    file_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    删除文件。
    """
    success = await delete_file(session, file_id, user.id)
    if success:
        return Result.success(message="删除成功")
    return Result.error("文件不存在或无权删除")