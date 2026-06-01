from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

class ResultOptions(BaseModel):
  code: int
  success: bool
  result: Any
  message: Optional[str] = None
  timeStamp: datetime = datetime.now()

class Result:
  @staticmethod
  def success(result: Optional[Any] = None, message: str = "操作成功"):
    return ResultOptions(code=200, success=True, result=result, message=message)
  
  @staticmethod
  def error(message: str = "操作失败"):
    return ResultOptions(code=400, success=False, result=None, message=message)
  
  @staticmethod
  def serve_error(message: str = "服务器错误"):
    return ResultOptions(code=500, success=False, result=None, message=message)
  
  @staticmethod
  def un_authorized(message: str = ""):
    return ResultOptions(code=401, success=False, result=None, message=message)
