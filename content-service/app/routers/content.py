import os
import hashlib
import threading
import time
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from prometheus_client import Gauge

router = APIRouter()

# Thread-safe counter for actual requests processed per second
REQUEST_COUNT = 0
counter_lock = threading.Lock()

# Custom Prometheus Gauge for exact second-by-second RPS
RPS_GAUGE = Gauge('service_rps_actual', 'Actual requests processed in the last second')

def rps_updater():
    global REQUEST_COUNT
    while True:
        time.sleep(1.0)
        with counter_lock:
            current_count = REQUEST_COUNT
            REQUEST_COUNT = 0
        RPS_GAUGE.set(current_count)

# Start background thread to update the gauge every second
threading.Thread(target=rps_updater, daemon=True).start()

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
    global REQUEST_COUNT
    with counter_lock:
        REQUEST_COUNT += 1

    # Simulate a lightweight billing check
    hash_val = hashlib.md5(b"billing_check").hexdigest()

    # Server-Side Render the clarknet.html template using cached sorted data
    return templates.TemplateResponse(
        request=request,
        name="clarknet.html",
        context={"users": MOCK_USERS_SORTED}
    )
