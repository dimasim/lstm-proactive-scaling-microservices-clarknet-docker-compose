import os
import random
import hashlib
from fastapi import APIRouter
from fastapi.responses import FileResponse

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

@router.get("/media")
def read_media():
    # 1. Select a large image randomly
    selected_image = random.choice(IMAGES)
    image_path = os.path.join(service_root, selected_image)

    # 2. Read the entire image into memory and calculate SHA-256 multiple times (CPU & RAM load)
    # Reading a 2MB - 4.5MB file into memory simulates memory footprints of image resizing/decoding
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            img_bytes = img_file.read()
        
        # Calculate SHA-256 hash multiple times to create a predictable CPU load
        sha_hash = img_bytes
        for _ in range(4):
            sha_hash = hashlib.sha256(sha_hash).digest()
        hash_hex = sha_hash.hex()
        
        # 3. Stream the file back to the client
        # Return FileResponse and set the hash in custom headers for verification
        return FileResponse(
            image_path,
            media_type="image/jpeg",
            headers={"X-Image-Hash": hash_hex}
        )
    
    # Fallback if image file is not found
    return {
        "status": "error",
        "message": f"Image {selected_image} not found in service root."
    }
