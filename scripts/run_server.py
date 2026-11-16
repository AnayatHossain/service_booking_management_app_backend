import os
import sys
import uvicorn

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings

if __name__ == "__main__":
    print(f"Starting Service Booking & Management Backend on {settings.host}:{settings.port}...")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=(settings.environment == "development"),
        access_log=True,
    )
