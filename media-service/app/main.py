from fastapi import FastAPI
from app.routers import media

app = FastAPI(
    title="ClarkNet Media Service",
    description="Microservice for serving media assets",
    version="1.0.0"
)

# Include routers
app.include_router(media.router)

@app.get("/health")
def health():
    return {"status": "healthy"}
