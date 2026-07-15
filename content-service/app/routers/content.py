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

# Pre-generate mock user sessions at startup to avoid loop overhead on each request
MOCK_USERS = []
for i in range(1, 151):
    username = f"clark_usr{i:03d}"
    ip = f"198.137.240.{i}"
    node = f"MD-BALT-NODE-{((i - 1) % 5) + 1}"
    baud = "28800" if i % 2 == 0 else "14400"
    duration = (i * 7) % 180
    
    MOCK_USERS.append({
        "username": username,
        "ip": ip,
        "node": node,
        "baud": baud,
        "duration": duration
    })

# Pre-sort users by connection duration descending (further CPU computation saved)
MOCK_USERS_SORTED = sorted(MOCK_USERS, key=lambda x: x["duration"], reverse=True)

@router.get("/content", response_class=HTMLResponse)
def read_content(request: Request):
    # Simulate a lightweight billing check
    hash_val = hashlib.md5(b"billing_check").hexdigest()

    # 3 MB per request creates a visible but safe RAM delta >100MB under concurrency
    temp_buffer = bytearray(3 * 1024 * 1024)
    temp_buffer[0] = 1
    temp_buffer[-1] = 1

    # Server-Side Render the clarknet.html template using cached sorted data
    return templates.TemplateResponse(
        request=request,
        name="clarknet.html",
        context={"users": MOCK_USERS_SORTED}
    )
