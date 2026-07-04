from fastapi import FastAPI
from app.routers import content

app = FastAPI(
    title="ClarkNet Content Service",
    description="Microservice for serving HTML content pages",
    version="1.0.0"
)

# Include routers
app.include_router(content.router)

@app.get("/health")
def health():
    return {"status": "healthy"}
