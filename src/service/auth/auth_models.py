from fastapi_fullauth import CreateUserSchema, UserSchema
from fastapi_fullauth.models.sqlmodel import RefreshTokenMixin, RoleMixin, UserMixin, UserRoleMixin
from pydantic import Field
from sqlmodel import Relationship


class RefreshToken(RefreshTokenMixin, table=True):
  pass

class Role(RoleMixin, table=True):
  pass

class UserRole(UserRoleMixin, table=True):
  pass

class User(UserMixin, table=True):
  user_name: str = Field(default="", max_length=50, index=True)
  roles: list[Role] = Relationship(link_model=UserRole)
  refresh_token: list[RefreshToken] = Relationship()

class AppUserSchema(UserSchema):
  pass

class AppCreateUserSchema(CreateUserSchema):
  user_name: str = ""
