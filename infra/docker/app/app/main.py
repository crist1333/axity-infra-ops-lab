from fastapi import FastAPI

app = FastAPI(title="Axity Infra Ops Lab", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Axity Infra Ops Lab"}

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}