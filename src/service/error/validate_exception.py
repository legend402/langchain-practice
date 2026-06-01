from fastapi.responses import JSONResponse


async def validation_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "success": False, "message": str(exc)},
    )