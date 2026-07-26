import uvicorn

if __name__ == "__main__":
    uvicorn.run("contextrepo.api:app", host="0.0.0.0", port=8420, reload=False)
