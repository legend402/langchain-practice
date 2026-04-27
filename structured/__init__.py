from structured.amap import *

class DefaultResult(BaseModel):
	""" 默认结果 """
	message: str = Field(description="返回消息")