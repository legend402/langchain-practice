from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from sqlalchemy import Column, ForeignKey, Integer, Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ChatSession(SQLModel, table=True):
    thread_id: str = Field(primary_key=True)
    title: Optional[str] = None
    user_id: Optional[UUID] = Field(default=None, foreign_key="fullauth_users.id")
    create_at: datetime = Field(default_factory=datetime.now)


class Roles(Enum):
    HUMAN = "human"
    AI = "ai"


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(
        default=None, sa_column=Column("id", Integer, Identity(), primary_key=True)
    )
    thread_id: str = Field(
        default=None,
        sa_column=Column(
            "thread_id", ForeignKey("chatsession.thread_id", ondelete="CASCADE")
        ),
    )
    role: str
    node_name: Optional[str] = None
    content: Optional[str] = None
    state: Optional[dict] = Field(default=None, sa_column=Column("state", JSONB))
    create_at: datetime = Field(default_factory=datetime.now)
