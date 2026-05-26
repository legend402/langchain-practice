from datetime import datetime
from typing import Optional
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ChatSession(SQLModel, table=True):
  thread_id: str = Field(primary_key=True)
  title: Optional[str] = None
  create_at: datetime = Field(default_factory=datetime.now)
  
class ChatMessage(SQLModel, table=True):
  id: int = Field(primary_key=True)
  thread_id: str = Field(foreign_key="chatsession.thread_id")
  role: str # "human" | "AI"
  node_name: Optional[str] = None
  content: Optional[str] = None
  state: Optional[dict] = Field(default=None, sa_column=Column("state", JSONB))
  create_at: datetime = Field(default_factory=datetime.now)