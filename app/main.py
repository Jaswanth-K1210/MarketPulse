"""
Main FastAPI Application — MarketPulse v2
Sets up FastAPI, CORS, routes, WebSocket, intelligence layer, and background tasks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
import logging
from datetime import datetime
from app.config import HOST, PORT
from app.api.routes import router
from app.routers.intelligence import router as intelligence_router
from app.routers.chat import router as chat_router
from app.api.websocket import websocket_endpoint, manager
from app.middleware.api_rate_limiter import APIRateLimiterMiddleware
from app.services.news_aggregator import news_aggregator_layer

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CREATE FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="MarketPulse-X API",
    description="Real-time multi-signal geopolitical and market intelligence platform",
    version="2.0.0"
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

# v2: API Rate Limiting
app.add_middleware(APIRateLimiterMiddleware)

# ═══════════════════════════════════════════════════════════════════════
# INCLUDE ROUTERS
# ═══════════════════════════════════════════════════════════════════════

app.include_router(router, prefix="/api")
app.include_router(intelligence_router)  # v2: Intelligence endpoints (/api/intelligence/*)
app.include_router(chat_router)  # OSINT: Natural language queries (/api/chat/*)

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
    logger.info("MARKETPULSE-X v2 STARTING UP")
    logger.info("="*70)

    # Initialize SQLite (pipeline data: articles, alerts, relationships)
    from app.services.database import init_db
    init_db()
    logger.info("SQLite database initialized")

    # Initialize MongoDB Atlas (user data: profiles, memory, sessions)
    from app.db.mongo import init_mongo
    mongo_ok = await init_mongo()
    if mongo_ok:
        logger.info("✅ MongoDB Atlas connected — user data layer active")
    else:
        logger.info("⚠️  MongoDB offline — user data stored in SQLite (fallback mode)")

    # v2: Initialize cache manager
    from app.services.infrastructure.cache_manager import get_cache_manager
    cache = get_cache_manager()
    logger.info(f"Cache manager initialized (bootstrap: {len(cache.bootstrap)} keys)")

    # v2: Initialize Redis if available
    import os
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(redis_url, decode_responses=True)
            cache.redis = redis_client
            logger.info(f"Redis connected: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, using memory-only cache: {e}")

    # Start background processing (news ingestion, alert generation)
    from app.services.background_scheduler import start_background_tasks
    start_background_tasks()
    logger.info("Background tasks started")

    # Start Alpaca WebSocket price stream (keeps price cache warm)
    try:
        from app.services.alpaca_service import alpaca_service
        if alpaca_service.available:
            _STREAM_TICKERS = ['AAPL', 'NVDA', 'AMD', 'INTC', 'TSM', 'MSFT', 'GOOGL', 'META', 'AMZN', 'AVGO']
            alpaca_service.start_stream(_STREAM_TICKERS)
            logger.info("✅ Alpaca WebSocket stream started for %d tickers", len(_STREAM_TICKERS))
        else:
            logger.info("⚠️  Alpaca keys not configured — using yfinance fallback for prices")
    except Exception as _alp_err:
        logger.warning("Alpaca stream startup failed (non-fatal): %s", _alp_err)

    logger.info("="*70)
    logger.info(f"MarketPulse-X v2 running at http://{HOST}:{PORT}")
    logger.info(f"API Documentation: http://{HOST}:{PORT}/docs")
    logger.info(f"Intelligence API: http://{HOST}:{PORT}/api/intelligence/risk-scores")
    logger.info("="*70 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("="*70)
    logger.info("🛑 MARKETPULSE-X SHUTTING DOWN")
    logger.info("="*70)
    from app.db.mongo import close_mongo
    await close_mongo()
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
        "version": "2.0.0",
        "status": "running",
        "description": "Real-time multi-signal geopolitical and market intelligence platform",
        "endpoints": {
            "api": "/api",
            "intelligence": "/api/intelligence",
            "risk_scores": "/api/intelligence/risk-scores",
            "signals": "/api/intelligence/signals",
            "correlations": "/api/intelligence/correlations",
            "macro": "/api/intelligence/macro",
            "market_overview": "/api/intelligence/market-overview",
            "conflict": "/api/intelligence/conflict",
            "docs": "/docs",
            "websocket": "/ws",
            "health": "/health",
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Enhanced health check with dependency status."""
    from app.services.infrastructure.cache_manager import get_cache_manager
    from app.services.infrastructure.circuit_breaker import (
        news_circuit, market_circuit, llm_circuit, conflict_circuit, macro_circuit
    )

    cache = get_cache_manager()

    health = {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "cache": cache.get_stats(),
        "circuit_breakers": {
            "news": {"status": news_circuit.status, "failures": news_circuit.failure_count},
            "market": {"status": market_circuit.status, "failures": market_circuit.failure_count},
            "llm": {"status": llm_circuit.status, "failures": llm_circuit.failure_count},
            "conflict": {"status": conflict_circuit.status, "failures": conflict_circuit.failure_count},
            "macro": {"status": macro_circuit.status, "failures": macro_circuit.failure_count},
        },
    }

    # Check Redis
    if cache.redis:
        try:
            await cache.redis.ping()
            health["redis"] = "connected"
        except Exception:
            health["redis"] = "disconnected"
    else:
        health["redis"] = "not_configured"

    return health
