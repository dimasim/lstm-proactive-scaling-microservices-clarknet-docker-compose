from fastapi import FastAPI
from app.routers import media
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="ClarkNet Media Service",
    description="Microservice for serving media assets",
    version="1.0.0"
)

# Include routers
app.include_router(media.router)

# Instrument and expose /metrics
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "healthy"}
