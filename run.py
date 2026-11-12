"""
NexusGuard Server Runner
Entrypoint for starting the FastAPI application with Uvicorn.
"""

import sys
import os
import uvicorn

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Starting NexusGuard server on http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
