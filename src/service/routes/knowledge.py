from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.service.auth.deps import CurrentUser
from src.service.db.database import get_session
from src.service.result import Result
from src.knowledge.service import (
    save_entry as _save_entry,
    delete_entry as _delete_entry,
    list_entries as _list_entries,
    search_knowledge as _search_knowledge,
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
):
    """
    检索知识库。
    """
    query = body.get("query", "")
    top_k = body.get("top_k", 5)
    if not query:
        return Result.error("查询内容不能为空")
    hits = await _search_knowledge(user.id, query, top_k)
    return Result.success(hits)