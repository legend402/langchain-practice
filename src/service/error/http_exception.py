from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

async def custom_http_exception_handler(request: Request, exc: HTTPException | TypeError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "success": False, "message": exc.detail}
    )