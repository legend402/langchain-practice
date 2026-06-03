from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import func
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


T = TypeVar("T", bound=SQLModel)

@dataclass
class PaginatedResult(Generic[T]):
  items: list[T]
  total: int
  page: int
  size: int
  pages: int = 0

  def __post_init__(self):
    self.pages = max(1, -(-self.total // self.size))

  @property
  def has_next(self) -> bool:
    return self.page < self.pages

  @property
  def has_prev(self) -> bool:
    return self.page > 1
  
async def pagination(
  session: AsyncSession,
  model: type[T],
  user_id_attr: str = "user_id",
  user_id: object = None,
  page: int = 1,
  size: int = 20,
  order_attr: str = "create_at",
  descending: bool = True,
  extra_filter: object | None = None
) -> PaginatedResult[T]:
  """
    通用数据库分页查询。
    参数:
        session: 数据库会话
        model: SQLModel 模型类
        user_id_attr: 用户 ID 字段名
        user_id: 用户 ID 值
        page: 页码（从 1 开始）
        size: 每页数量
        order_attr: 排序字段名
        descending: 是否降序
        extra_filter: 额外过滤条件
    返回:
        PaginatedResult 分页结果
  """
  query = select(model)
  if user_id is not None:
    query = query.where(getattr(model, user_id_attr) == user_id)
  if extra_filter is not None:
    query = query.where(extra_filter)

  count_query = select(func.count()).select_from(query.subquery())
  total = await session.scalar(count_query)

  order_col = getattr(model, order_attr)
  query = query.order_by(order_col.desc() if descending else order_col.asc())
  offset = (page - 1) * size
  query = query.offset(offset).limit(size)

  result = await session.exec(query)
  items = list(result.all())

  return PaginatedResult(items=items, total=total, page=page, size=size)