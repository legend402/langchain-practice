from pydantic import BaseModel, Field

class DistanceResult(BaseModel):
	""" 距离查询结果 """
	loc1: str = Field(description="出发地")
	loc2: str = Field(description="目的地")
	distance: float = Field(description="距离")

class RoutePlanResult(BaseModel):
	""" 路线规划结果 """
	start_location: str = Field(description="起点")
	end_location: str = Field(description="终点")
	steps: list[str] = Field(description="路线步骤")
