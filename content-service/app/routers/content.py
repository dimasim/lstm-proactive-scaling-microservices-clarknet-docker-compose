import os
import hashlib
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Setup robust path for templates directory
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates_dir = os.path.join(current_dir, "templates")
templates = Jinja2Templates(directory=templates_dir)

@router.get("/content", response_class=HTMLResponse)
def read_content(request: Request):
    # 1. Generate 150 mock dial-up user sessions dynamically
    users = []
    for i in range(1, 151):
        username = f"clark_usr{i:03d}"
        ip = f"198.137.240.{i}"
        node = f"MD-BALT-NODE-{((i - 1) % 5) + 1}"
        baud = "28800" if i % 2 == 0 else "14400"
        duration = (i * 7) % 180
        
        # 2. Simulate database decryption/billing checks (CPU-bound)
        # We calculate MD5 hash 600 times for each user session to create realistic CPU load
        data_str = f"{username}-{ip}-{node}-{baud}-{duration}"
        hash_val = data_str.encode()
        for _ in range(600):
            hash_val = hashlib.md5(hash_val).hexdigest().encode()

        users.append({
            "username": username,
            "ip": ip,
            "node": node,
            "baud": baud,
            "duration": duration
        })

    # Sort users by connection duration descending (further CPU computation)
    users_sorted = sorted(users, key=lambda x: x["duration"], reverse=True)

    # 3. Server-Side Render the clarknet.html template using keyword arguments
    return templates.TemplateResponse(
        request=request,
        name="clarknet.html",
        context={"users": users_sorted}
    )
