"""
MarketPulse-X Entry Point
Run this file to start the backend server
"""

import uvicorn
from app.config import HOST, PORT, DEBUG

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting MarketPulse-X Backend Server")
    print("=" * 70)
    print(f"Host: {HOST}")
    print(f"Port: {PORT}")
    print(f"Debug: {DEBUG}")
    print("=" * 70)
    print()

    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info"
    )
