import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.service:app", port=7900, reload=True, host="0.0.0.0")
