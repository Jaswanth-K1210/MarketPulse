"""
Main FastAPI Application
Sets up FastAPI, CORS, routes, WebSocket, and background tasks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime
from app.config import FRONTEND_URL, NEWS_FETCH_INTERVAL, HOST, PORT, FINNHUB_FETCH_INTERVAL, GOOGLE_NEWS_FETCH_INTERVAL, NEWSAPI_FETCH_INTERVAL, NEWSDATA_FETCH_INTERVAL
from app.api.routes import router
from app.api.websocket import websocket_endpoint, manager
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database

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
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════
# INCLUDE ROUTERS
# ═══════════════════════════════════════════════════════════════════════

app.include_router(router, prefix="/api")

# ═══════════════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ═══════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts"""
    await websocket_endpoint(websocket)

# ═══════════════════════════════════════════════════════════════════════
# BACKGROUND TASKS
# ═══════════════════════════════════════════════════════════════════════

scheduler = AsyncIOScheduler()


async def news_monitoring_task():
    """Background task: Fetch and process news every N minutes"""
    try:
        logger.info("="*70)
        logger.info(f"NEWS MONITORING TASK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)

        # Fetch news from all sources
        articles = news_aggregator.fetch_all()

        if not articles:
            logger.info("No new articles found")
            return

        logger.info(f"Fetched {len(articles)} articles")

        # CRITICAL: Save ALL articles to database immediately (before processing)
        # This ensures fresh articles are available even if Gemini processing fails
        logger.info("💾 Saving articles to database...")
        articles_saved = 0
        for article in articles:
            try:
                database.save_article(article)
                articles_saved += 1
            except Exception as e:
                logger.warning(f"Failed to save article {article.title[:50]}: {str(e)}")
        logger.info(f"✓ Saved {articles_saved}/{len(articles)} articles to database")

        logger.info(f"Processing {len(articles)} articles...")

        # Process each article through pipeline
        alerts_generated = 0
        for article in articles:
            try:
                alert = pipeline.process_article(article)
                if alert:
                    alerts_generated += 1
                    # Broadcast alert via WebSocket
                    await manager.broadcast_alert(alert.to_dict())
            except Exception as e:
                logger.error(f"Error processing article {article.title[:50]}: {str(e)}")
                # Continue with next article - article is already saved above
                continue

        logger.info(f"Generated {alerts_generated} alerts from {len(articles)} articles")
        logger.info("="*70 + "\n")

    except Exception as e:
        logger.error(f"Error in news monitoring task: {str(e)}", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# STARTUP & SHUTDOWN EVENTS
# ═══════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("="*70)
    logger.info("🚀 MARKETPULSE-X STARTING UP")
    logger.info("="*70)

    # Initialize default portfolio if none exists
    if not database.get_portfolio():
        from app.config import DEFAULT_PORTFOLIO
        database.save_portfolio({
            "user_name": "Jaswanth",
            "portfolio": DEFAULT_PORTFOLIO
        })
        logger.info("✓ Initialized default portfolio for Jaswanth")

    # Start background scheduler
    # HYBRID INTERVAL SCHEDULING - Optimized for Gemini free tier
    # Different sources fetch at different intervals to respect rate limits
    
    scheduler.add_job(
        news_monitoring_task,
        trigger=IntervalTrigger(minutes=FINNHUB_FETCH_INTERVAL),
        id="news_monitoring",
        name="News Monitoring Task (Finnhub + Google News)",
        replace_existing=True
    )

    scheduler.start()
    logger.info("="*70)
    logger.info("✓ HYBRID SCHEDULING ENABLED (Gemini Budget Mode)")
    logger.info(f"  • Primary (Finnhub + Google News): Every {FINNHUB_FETCH_INTERVAL} min")
    logger.info(f"  • Secondary (NewsAPI): Every {NEWSAPI_FETCH_INTERVAL} min")
    logger.info(f"  • Tertiary (NewsData.io): Every {NEWSDATA_FETCH_INTERVAL} min")
    logger.info("✓ Gemini free tier protected: 20 RPM limit (~200 calls/day)")
    logger.info("="*70)

    # Run news monitoring immediately on startup
    logger.info("✓ Running initial news fetch...")
    await news_monitoring_task()

    logger.info("="*70)
    logger.info(f"✅ MarketPulse-X is running at http://{HOST}:{PORT}")
    logger.info(f"✅ API Documentation: http://{HOST}:{PORT}/docs")
    logger.info(f"✅ WebSocket endpoint: ws://{HOST}:{PORT}/ws")
    logger.info(f"✅ Gemini Budget: Protected for hackathon mode")
    logger.info("="*70 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("="*70)
    logger.info("🛑 MARKETPULSE-X SHUTTING DOWN")
    logger.info("="*70)

    # Shutdown scheduler
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✓ Background tasks stopped")

    logger.info("✅ MarketPulse-X shut down successfully")
    logger.info("="*70 + "\n")


# ═══════════════════════════════════════════════════════════════════════
# ROOT ENDPOINT
# ═══════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Root endpoint"""
    stats = database.get_stats()

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
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }
