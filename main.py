from fastapi import FastAPI

app = FastAPI(title="Network Security Project API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Network Security Project API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}