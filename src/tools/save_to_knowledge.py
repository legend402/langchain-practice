from langchain_community.tools import tool


@tool
async def save_to_knowledge(title: str, content: str) -> str:
  """
  将内容存入用户知识库。当用户明确要求存入知识库时调用。
  用户说"存入知识库"、"记录下来"、"保存到知识库"等类似意图时触发。
  :title str: 知识标题
  :content str: 要存入的完整内容
  """
  from src.service.db.database import engine
  from sqlmodel.ext.asyncio.session import AsyncSession
  from src.knowledge.service import save_entry
  from src.utils.agent import get_current_user_id

  user_id = get_current_user_id()
  if not user_id:
      return "无法获取用户信息，请先登录"

  from uuid import UUID
  async with AsyncSession(engine) as session:
      entry = await save_entry(
          session=session,
          user_id=UUID(user_id),
          title=title,
          content=content,
          source_type="manual",
      )
      return f"已成功存入知识库，标题: {entry.title}，共 {entry.chunk_count} 个分块"