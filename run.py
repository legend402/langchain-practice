import uvicorn

uvicorn.run("src.service:app", port=4030, reload=True)
