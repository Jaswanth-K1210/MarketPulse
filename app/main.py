"""
Main FastAPI Application
Sets up FastAPI, CORS, routes, WebSocket, and background tasks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
import logging
from datetime import datetime
from app.config import HOST, PORT
from app.api.routes import router
from app.api.websocket import websocket_endpoint, manager
from app.services.news_aggregator import news_aggregator_layer

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CREATE FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="MarketPulse-X API",
    description="Real-time supply chain intelligence for portfolio management",
    version="1.0.0"
)

# ═══════════════════════════════════════════════════════════════════════
# CORS CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════
# INCLUDE ROUTERS
# ═══════════════════════════════════════════════════════════════════════

app.include_router(router, prefix="/api")

# ═══════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT (Optional - not required for demo)
# ═══════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts"""
    try:
        await websocket_endpoint(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# ═══════════════════════════════════════════════════════════════════════
# STARTUP & SHUTDOWN EVENTS
# ═══════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("="*70)
    logger.info("🚀 MARKETPULSE-X STARTING UP")
    logger.info("="*70)
    
    # Initialize database
    from app.services.database import init_db
    init_db()
    logger.info("✓ Database initialized")

    logger.info("="*70)
    logger.info(f"✅ MarketPulse-X is running at http://{HOST}:{PORT}")
    logger.info(f"✅ API Documentation: http://{HOST}:{PORT}/docs")
    logger.info(f"✅ Demo Frontend: Open frontend/demo.html")
    logger.info("="*70 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("="*70)
    logger.info("🛑 MARKETPULSE-X SHUTTING DOWN")
    logger.info("="*70)
    logger.info("✅ MarketPulse-X shut down successfully")
    logger.info("="*70 + "\n")


# ═══════════════════════════════════════════════════════════════════════
# ROOT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MarketPulse-X API",
        "version": "1.0.0",
        "status": "running",
        "description": "Real-time supply chain intelligence for portfolio management",
        "endpoints": {
            "api": "/api",
            "docs": "/docs",
            "websocket": "/ws"
        },
        "timestamp": datetime.now().isoformat()
    }
