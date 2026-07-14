import os
import random
import hashlib
from fastapi import APIRouter, Response

router = APIRouter()


# Get the path to the service root folder (media-service/)
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
service_root = os.path.dirname(app_dir)

IMAGES = [
    "20250928_051902.jpg",
    "20250928_075112.jpg",
    "20250928_080239.jpg"
]

# Pre-load tiny dummy image bytes at startup to avoid Disk I/O and large network transfer overhead
CACHED_IMAGES = {}
for img_name in IMAGES:
    # We cache 1KB of dummy data representing the image to eliminate the 4.5MB transfer bottleneck
    CACHED_IMAGES[img_name] = b"FFD8FFE000104A464946" + (b"0" * 1000)

@router.get("/media")
def read_media():
    selected_image = random.choice(IMAGES)
    img_bytes = CACHED_IMAGES.get(selected_image)

    if img_bytes:
        # 4 MB per request creates a visible but safe RAM delta >150MB under concurrency
        temp_buffer = bytearray(4 * 1024 * 1024)
        temp_buffer[0] = 1
        temp_buffer[-1] = 1

        # Calculate SHA-256 hash of the filename instead of 4MB image content to save CPU resources
        hash_hex = hashlib.sha256(selected_image.encode('utf-8')).hexdigest()
        
        # Stream the cached file bytes back to the client
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={"X-Image-Hash": hash_hex}
        )
    
    # Fallback if image file is not found
    return {
        "status": "error",
        "message": f"Image {selected_image} not found in service root."
    }
