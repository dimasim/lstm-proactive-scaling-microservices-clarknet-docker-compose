from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

@app.get("/content", response_class=HTMLResponse)
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

@app.get("/api")
def read_api():
    # Simulate dynamic/CGI CPU-heavy calculation
    # Running fibonacci(28) takes a small fraction of a second but utilizes the CPU
    result = fibonacci(28)
    return {
        "status": "ok",
        "service": "content-service",
        "endpoint": "dynamic_api",
        "calculation_result": result,
        "message": "Calculated Fibonacci(28) to simulate CPU load"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
