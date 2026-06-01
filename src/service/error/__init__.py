from fastapi import FastAPI
from src.service.error.http_exception import custom_http_exception_handler
from src.service.error.validate_exception import validation_handler

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

def register_error_handler(app: FastAPI):
  app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
  app.add_exception_handler(RequestValidationError, validation_handler)