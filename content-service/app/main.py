from fastapi import FastAPI
from app.routers import content
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="ClarkNet Content Service",
    description="Microservice for serving HTML content pages",
    version="1.0.0"
)

# Include routers
app.include_router(content.router)

# Instrument and expose /metrics
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "healthy"}
