from fastapi import APIRouter

router = APIRouter()

@router.get("/media")
def read_media():
    # Simulate serving a small static media metadata or asset response
    return {
        "status": "ok",
        "service": "media-service",
        "type": "image/jpeg",
        "size_bytes": 10240,
        "message": "Serving mock media asset"
    }
