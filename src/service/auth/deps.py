from typing import Annotated

from fastapi import Depends
from fastapi_fullauth.dependencies import current_user

from src.service.auth.auth_models import AppUserSchema

CurrentUser = Annotated[AppUserSchema, Depends(current_user)]
