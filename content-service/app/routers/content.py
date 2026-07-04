from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/content", response_class=HTMLResponse)
def read_content():
    # Simulate serving standard static HTML content pages
    return """
    <html>
        <head><title>Mock Content Service</title></head>
        <body>
            <h1>ClarkNet Content Service</h1>
            <p>This is a simulated static HTML content page.</p>
        </body>
    </html>
    """
