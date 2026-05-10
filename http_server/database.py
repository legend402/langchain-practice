import os

from sqlalchemy import Column, DateTime, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class UploadRecord(Base):
    """上传文件记录表"""
    __tablename__ = "upload"

    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


def create_mysql_engine():
    """创建 MySQL 引擎"""
    db_uri = os.getenv("MYSQL_DB_URI")
    if not db_uri:
        raise ValueError("MYSQL_DB_URI 环境变量未设置")
    engine = create_engine(db_uri, pool_pre_ping=True)
    return engine


def init_db(engine):
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    """获取 Session 工厂"""
    return sessionmaker(bind=engine)
