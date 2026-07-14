from fastapi import FastAPI
from app.routers import media
from prometheus_fastapi_instrumentator import Instrumentator
import threading
import gc
import ctypes
import time

def start_memory_trimmer():
    def memory_trimmer():
        try:
            libc = ctypes.CDLL("libc.so.6")
        except Exception:
            libc = None
            
        while True:
            time.sleep(1)
            gc.collect()
            if libc:
                try:
                    libc.malloc_trim(0)
                except Exception:
                    pass
    
    t = threading.Thread(target=memory_trimmer, daemon=True)
    t.start()

start_memory_trimmer()

app = FastAPI(
    title="ClarkNet Media Service",
    description="Microservice for serving media assets",
    version="1.0.0"
)

# Include routers
app.include_router(media.router)

# Instrument and expose /metrics
Instrumentator().instrument(app).expose(app)

@app.get("/health")
def health():
    return {"status": "healthy"}
