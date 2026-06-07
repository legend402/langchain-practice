import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.auth.deps import CurrentUser
from src.service.db.database import get_session
from src.service.result import Result
from src.knowledge.service import (
    save_entry_v2 as _save_entry,
    delete_entry_v2 as _delete_entry,
    list_entries as _list_entries,
    search_knowledge_v2 as _search_knowledge_v2,
    search_entries as _search_entries,
    save_entry_v2_async,
    get_task_status,
    list_active_tasks,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class CreateEntryRequest(BaseModel):
    title: str
    content: Optional[str] = None
    file_id: Optional[str] = None
    source_type: str = "manual"
    source_id: Optional[str] = None


@router.post("/entries")
async def create_entry(
    body: CreateEntryRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    存入知识条目。
    """
    if not body.content and not body.file_id:
        return Result.error("content 和 file_id 至少提供一个")

    entry = await _save_entry(
        session=session,
        user_id=user.id,
        title=body.title,
        content=body.content,
        file_id=body.file_id,
        source_type=body.source_type,
        source_id=body.source_id,
    )
    return Result.success(entry)


@router.post("/entries/async")
async def create_entry_async(
    body: CreateEntryRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    异步存入知识条目（PDF 等大文件）。
    立即返回 task_id，前端通过 SSE 轮询进度。
    """
    if not body.file_id:
        return Result.error("异步上传必须提供 file_id")

    from src.service.controller.FileUpload import get_file_record
    record = await get_file_record(session, file_id=body.file_id)
    if not record:
        return Result.error("文件记录不存在")

    task_id = await save_entry_v2_async(
        user_id=user.id,
        title=body.title,
        file_path=record.file_path,
        source_type=body.source_type,
        source_id=body.source_id or body.file_id,
    )
    return Result.success({"task_id": task_id})


@router.get("/entries")
async def get_entries(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    获取当前用户知识条目列表。
    """
    result = await _list_entries(session, user.id, page, size)
    return Result.success(result)


@router.get("/entries/{entry_id}")
async def get_entry_detail(
    entry_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    获取单个知识条目详情。
    """
    from src.service.db.db import KnowledgeEntry
    entry = await session.get(KnowledgeEntry, entry_id)
    if not entry or str(entry.user_id) != str(user.id):
        return Result.error("知识条目不存在")
    return Result.success(entry)


@router.delete("/entries/{entry_id}")
async def delete_entry_route(
    entry_id: str,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    删除知识条目。
    """
    success = await _delete_entry(session, user.id, entry_id)
    if success:
        return Result.success(message="删除成功")
    return Result.error("知识条目不存在或无权删除")


@router.post("/search")
async def search_route(
    body: dict,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    """
    检索知识库，返回带页码、章节等溯源信息的结果。
    """
    query = body.get("query", "")
    top_k = body.get("top_k", 20)
    if not query:
        return Result.error("查询内容不能为空")
    hits = await _search_knowledge_v2(user.id, query, top_k)
    results = []
    for h in hits:
        item = {
            "entry_id": h.entry_id,
            "chunk_index": h.chunk_index,
            "text": h.text,
            "score": h.score,
            "page_start": h.page_start,
            "page_end": h.page_end,
            "heading_path": h.heading_path,
            "content_type": h.content_type,
            "table_id": h.table_id,
        }
        results.append(item)
    return Result.success(results)


@router.get("/tasks/active")
async def get_active_tasks(user: CurrentUser):
    """
    获取当前用户所有进行中的解析任务。
    前端页面刷新后调用此接口恢复进度监听。
    """
    tasks = await list_active_tasks(user.id)
    return Result.success(tasks)


@router.get("/tasks/{task_id}/progress")
async def task_progress(task_id: str):
    """
    SSE 推送解析任务进度。
    前端通过 EventSource 连接，实时接收状态更新。
    任务完成后自动断开。
    """

    async def _stream():
        last_status = None
        while True:
            status = await get_task_status(task_id)
            if status is None:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break

            if status != last_status:
                yield f"data: {json.dumps(status)}\n\n"
                last_status = dict(status)

            if status.get("status") in ("completed", "failed"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(_stream(), media_type="text/event-stream")
