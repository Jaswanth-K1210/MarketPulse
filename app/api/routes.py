"""
REST API Routes
Endpoints for portfolio, alerts, graphs, and market data
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict
from pydantic import BaseModel
import logging
from app.services.database import database
from app.services.market_data import market_data_service
from app.services.stock_data import stock_data_service
from app.models.alert import Alert
from app.models.article import Article

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════

class PortfolioRequest(BaseModel):
    user_name: str
    portfolio: List[Dict]


class AgentQuestionRequest(BaseModel):
    question: str
    context: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = database.get_stats()
        return {
            "status": "ok",
            "timestamp": "2025-12-12",
            "database": stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


# ═══════════════════════════════════════════════════════════════════════
# STOCK PRICE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/stock-prices")
async def get_stock_prices(tickers: Optional[str] = None):
    """
    Get live stock prices from yfinance
    
    Query params:
        tickers: Comma-separated list of tickers (e.g., "AAPL,NVDA,AMD")
                 If not provided, returns default portfolio tickers
    """
    try:
        # Default portfolio tickers
        default_tickers = ['AAPL', 'NVDA', 'AMD', 'INTC', 'AVGO']
        
        # Parse tickers from query param
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',')]
        else:
            ticker_list = default_tickers
        
        # Fetch live prices
        prices = stock_data_service.get_live_prices(ticker_list)
        
        return {
            "status": "success",
            "count": len(prices),
            "data": prices,
            "timestamp": prices[ticker_list[0]]['timestamp'] if prices else None
        }
    except Exception as e:
        logger.error(f"Error fetching stock prices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# PORTFOLIO ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.post("/portfolio")
async def set_portfolio(request: PortfolioRequest):
    """Store user's portfolio"""
    try:
        portfolio_data = {
            "user_name": request.user_name,
            "portfolio": request.portfolio
        }
        database.save_portfolio(portfolio_data)

        # Calculate current portfolio value
        portfolio_value = market_data_service.get_portfolio_value(request.portfolio)

        return {
            "status": "success",
            "message": f"Portfolio saved for {request.user_name}",
            "portfolio_value": portfolio_value
        }
    except Exception as e:
        logger.error(f"Error saving portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio")
async def get_portfolio():
    """Get current portfolio with live prices"""
    try:
        portfolio_data = database.get_portfolio()
        if not portfolio_data:
            # Return default portfolio
            from app.config import DEFAULT_PORTFOLIO
            portfolio_data = {"user_name": "Jaswanth", "portfolio": DEFAULT_PORTFOLIO}

        holdings = portfolio_data.get('portfolio', [])

        # Enrich holdings with current market data
        enriched_holdings = []
        total_value = 0
        total_cost = 0

        for holding in holdings:
            ticker = holding.get('ticker')
            quantity = holding.get('quantity', 0)
            purchase_price = holding.get('purchase_price', 0)

            # Get live market data
            market_data = market_data_service.get_stock_data(ticker)

            if market_data:
                current_price = market_data.get('current_price', 0)
                current_value = current_price * quantity
                cost_basis = purchase_price * quantity
                gain_loss = current_value - cost_basis
                gain_loss_percent = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

                enriched_holding = {
                    **holding,
                    "current_price": current_price,
                    "current_value": round(current_value, 2),
                    "cost_basis": round(cost_basis, 2),
                    "gain_loss": round(gain_loss, 2),
                    "gain_loss_percent": round(gain_loss_percent, 2),
                    "day_change": market_data.get('change', 0),
                    "day_change_percent": market_data.get('change_percent', 0)
                }

                enriched_holdings.append(enriched_holding)
                total_value += current_value
                total_cost += cost_basis
            else:
                # If market data fails, use purchase price
                enriched_holdings.append({
                    **holding,
                    "current_price": purchase_price,
                    "current_value": purchase_price * quantity,
                    "cost_basis": purchase_price * quantity,
                    "gain_loss": 0,
                    "gain_loss_percent": 0,
                    "day_change": 0,
                    "day_change_percent": 0
                })

        return {
            "user_name": portfolio_data.get('user_name', 'Jaswanth'),
            "holdings": enriched_holdings,
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_gain_loss": round(total_value - total_cost, 2),
            "total_gain_loss_percent": round((total_value - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting portfolio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# ALERT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/alerts")
async def get_alerts(
    limit: int = 50,
    severity: Optional[str] = None,
    include_demo: bool = True
):
    """Get recent alerts (includes demo alerts by default)"""
    try:
        if severity:
            alerts = database.get_alerts_by_severity(severity, limit)
        else:
            alerts = database.get_all_alerts(limit)
        
        # Add demo alerts if requested and we have fewer than 4 alerts
        if include_demo and len(alerts) < 4:
            demo_alerts = _get_demo_alerts()
            # Merge demo alerts with real alerts, avoiding duplicates
            existing_ids = {alert.id for alert in alerts}
            for demo_alert in demo_alerts:
                if demo_alert.id not in existing_ids:
                    alerts.append(demo_alert)
                    if len(alerts) >= 4:
                        break

        return {
            "count": len(alerts),
            "alerts": [alert.to_dict() for alert in alerts]
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_demo_alerts():
    """Generate demo alerts for testing/demo purposes"""
    from app.models.alert import Alert, AffectedHolding
    from datetime import datetime, timedelta
    
    demo_alerts = []
    
    # Demo Alert 1: TSMC Supply Chain Disruption (HIGH)
    alert1 = Alert(
        id="alert_demo_001",
        type="relationship_based",
        severity="high",
        trigger_article_id="demo_001",
        affected_holdings=[
            AffectedHolding(
                company="Apple",
                ticker="AAPL",
                quantity=150,
                impact_percent=-2.5,
                impact_dollar=-587.50,
                current_price=198.75
            ),
            AffectedHolding(
                company="NVIDIA",
                ticker="NVDA",
                quantity=80,
                impact_percent=-1.8,
                impact_dollar=-205.80,
                current_price=875.50
            ),
            AffectedHolding(
                company="AMD",
                ticker="AMD",
                quantity=120,
                impact_percent=-1.2,
                impact_dollar=-201.60,
                current_price=168.30
            )
        ],
        impact_percent=-2.1,
        impact_dollar=-994.90,
        confidence=0.94,
        chain={
            "level1": "TSMC Halt",
            "level2": "Apple/NVIDIA Shortage",
            "level3": "Portfolio Impact"
        },
        sources=[
            "https://newsapi.org/tsmc-halt",
            "https://reuters.com/tsmc-supply"
        ],
        explanation="Taiwan Semiconductor Manufacturing Company (TSMC) announced an unexpected 2-week production halt. With TSMC supplying 100% of Apple's A-series chips and significant portions of NVIDIA's GPU orders, this disruption will likely impact your holdings. Historical data suggests 1-2% portfolio impact per week of disruption.",
        recommendation="HOLD & MONITOR",
        created_at=datetime.now() - timedelta(hours=2)
    )
    alert1.tags = ["supply-chain", "semiconductor", "critical"]
    demo_alerts.append(alert1)
    
    # Demo Alert 2: Intel Fab Delay (MEDIUM)
    alert2 = Alert(
        id="alert_demo_002",
        type="direct_impact",
        severity="medium",
        trigger_article_id="demo_002",
        affected_holdings=[
            AffectedHolding(
                company="Intel",
                ticker="INTC",
                quantity=200,
                impact_percent=-1.5,
                impact_dollar=-96.30,
                current_price=36.45
            )
        ],
        impact_percent=-1.5,
        impact_dollar=-96.30,
        confidence=0.87,
        chain={
            "level1": "Intel Fab Delay",
            "level2": "Manufacturing Setback",
            "level3": "Stock Impact"
        },
        sources=[
            "https://reuters.com/intel-fab"
        ],
        explanation="Intel Corporation announced a 6-month delay in opening its new Arizona fab facility. This could impact their competitive position in AI chip manufacturing. Your 200 Intel shares may see short-term pressure.",
        recommendation="MONITOR",
        created_at=datetime.now() - timedelta(days=1)
    )
    alert2.tags = ["manufacturing", "delay", "intel"]
    demo_alerts.append(alert2)
    
    # Demo Alert 3: NVIDIA AI Chip Sales Surge (POSITIVE)
    alert3 = Alert(
        id="alert_demo_003",
        type="positive_impact",
        severity="low",
        trigger_article_id="demo_003",
        affected_holdings=[
            AffectedHolding(
                company="NVIDIA",
                ticker="NVDA",
                quantity=80,
                impact_percent=3.2,
                impact_dollar=456.80,
                current_price=875.50
            ),
            AffectedHolding(
                company="Broadcom",
                ticker="AVGO",
                quantity=60,
                impact_percent=1.5,
                impact_dollar=170.10,
                current_price=795.20
            )
        ],
        impact_percent=2.8,
        impact_dollar=626.90,
        confidence=0.91,
        chain={
            "level1": "NVIDIA AI Demand ↑",
            "level2": "Strong Q4 Sales",
            "level3": "Stock Gains"
        },
        sources=[
            "https://techcrunch.com/nvidia-surge"
        ],
        explanation="NVIDIA reported unprecedented demand for their AI chips from major cloud providers. This positive news suggests strong Q4 and Q1 earnings potential. Your holdings stand to benefit from continued AI momentum.",
        recommendation="HOLD",
        created_at=datetime.now() - timedelta(days=2)
    )
    alert3.tags = ["positive", "ai", "demand"]
    demo_alerts.append(alert3)
    
    # Demo Alert 4: Broadcom Supply Concerns (MEDIUM)
    alert4 = Alert(
        id="alert_demo_004",
        type="relationship_based",
        severity="medium",
        trigger_article_id="demo_004",
        affected_holdings=[
            AffectedHolding(
                company="Broadcom",
                ticker="AVGO",
                quantity=60,
                impact_percent=-0.8,
                impact_dollar=-90.80,
                current_price=795.20
            )
        ],
        impact_percent=-0.8,
        impact_dollar=-90.80,
        confidence=0.79,
        chain={
            "level1": "Broadcom Supply Issues",
            "level2": "Reduced Revenue",
            "level3": "Stock Pressure"
        },
        sources=[
            "https://ft.com/broadcom-supply"
        ],
        explanation="Industry sources indicate Broadcom is experiencing unexpected supply constraints in certain product lines. This may impact Q4 guidance and revenues. Keep a close eye on upcoming earnings calls.",
        recommendation="MONITOR",
        created_at=datetime.now() - timedelta(days=3)
    )
    alert4.tags = ["supply", "broadcom", "constraint"]
    demo_alerts.append(alert4)
    
    return demo_alerts


@router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get specific alert"""
    try:
        alert = database.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        return alert.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/graph/{alert_id}")
async def get_knowledge_graph(alert_id: str):
    """Get knowledge graph for alert"""
    try:
        graph = database.get_knowledge_graph(alert_id)
        if not graph:
            raise HTTPException(status_code=404, detail="Knowledge graph not found")

        return graph.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting knowledge graph: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# MARKET DATA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/market-data/{ticker}")
async def get_market_data(ticker: str):
    """Get current market data for a ticker"""
    try:
        data = market_data_service.get_stock_data(ticker)
        if not data:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/multiple/{tickers}")
async def get_multiple_market_data(tickers: str):
    """Get market data for multiple tickers (comma-separated)"""
    try:
        ticker_list = [t.strip() for t in tickers.split(',')]
        data = market_data_service.get_multiple_stocks(ticker_list)

        return {
            "count": len(data),
            "stocks": data
        }
    except Exception as e:
        logger.error(f"Error getting multiple market data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# AGENT QUESTION ENDPOINT (Placeholder - will be implemented in Phase 2)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/agent-question")
async def ask_agent_question(request: AgentQuestionRequest):
    """Ask multi-agent system a question"""
    try:
        # Placeholder - will implement with multi-agent system in Phase 2
        return {
            "query": request.question,
            "status": "not_implemented",
            "message": "Multi-agent system will be implemented in Phase 2"
        }
    except Exception as e:
        logger.error(f"Error processing agent question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# ARTICLES ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@router.get("/articles")
async def get_articles(limit: int = 10):
    """Get recent articles (default: 10), sorted by most recent first"""
    try:
        articles = database.get_all_articles(limit)
        return {
            "count": len(articles),
            "articles": [article.to_dict() for article in articles]
        }
    except Exception as e:
        logger.error(f"Error getting articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-news")
async def fetch_news_only(limit: int = 10):
    """
    Fetch news articles and save to database WITHOUT processing
    Useful when Gemini API limit is reached - still get fresh articles
    """
    try:
        from app.services.news_aggregator import news_aggregator
        
        logger.info(f"📰 Fetching news only (no processing) - limit: {limit}")
        
        # Clear cache for fresh fetch
        news_aggregator.clear_seen_urls()
        
        # Fetch news
        articles = news_aggregator.fetch_all(limit=limit)
        
        if not articles:
            return {
                "status": "success",
                "message": "No new articles found",
                "articles_fetched": 0,
                "articles_saved": 0
            }
        
        # Save all articles to database
        articles_saved = 0
        for article in articles:
            try:
                database.save_article(article)
                articles_saved += 1
            except Exception as e:
                logger.warning(f"Failed to save article: {str(e)}")
        
        logger.info(f"✅ Saved {articles_saved}/{len(articles)} articles")
        
        return {
            "status": "success",
            "message": f"Fetched and saved {articles_saved} articles",
            "articles_fetched": len(articles),
            "articles_saved": articles_saved
        }
    except Exception as e:
        logger.error(f"Error in fetch-news: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/fetch-status")
async def get_fetch_status():
    """Get current news fetching processing status"""
    try:
        from app.services.news_aggregator import news_aggregator
        status = news_aggregator.get_processing_status()
        return status
    except Exception as e:
        logger.error(f"Error getting fetch status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# FULL PIPELINE ENDPOINT - FETCH & ANALYZE NEWS
# ═══════════════════════════════════════════════════════════════════════

@router.post("/fetch-and-analyze")
async def fetch_and_analyze_news(limit: int = 4):
    """
    Fetch news and run full pipeline with multi-agent analysis

    This endpoint:
    1. Fetches latest news from all sources (Phase 1)
    2. Processes through multi-agent system (Phase 2)
    3. Returns results for UI display (Phase 3)
    """
    try:
        from app.services.news_aggregator import news_aggregator
        from app.services.pipeline import pipeline

        logger.info(f"🚀 Starting fetch & analyze pipeline (limit: {limit})")

        # Clear cache for fresh fetch
        news_aggregator.clear_seen_urls()

        # Phase 1: Fetch news
        logger.info("📰 Phase 1: Fetching news...")
        articles = news_aggregator.fetch_all(limit=limit)

        if not articles:
            return {
                "status": "success",
                "message": "No new articles found",
                "articles_fetched": 0,
                "alerts_generated": 0,
                "results": []
            }

        logger.info(f"✓ Fetched {len(articles)} articles")

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

        # Phase 2: Process through enhanced pipeline
        logger.info("⚙️  Phase 2: Processing through multi-agent pipeline...")
        results = []
        alerts_generated = 0

        for i, article in enumerate(articles, 1):
            logger.info(f"\n[{i}/{len(articles)}] Processing: {article.title[:60]}...")

            try:
                # Use enhanced pipeline with agents
                result = pipeline.process_article_with_agents(article)

                if result:
                    results.append({
                        "article": {
                            "id": article.id,
                            "title": article.title,
                            "url": article.url,
                            "source": article.source,
                            "published_at": article.published_at.isoformat(),
                            "companies_mentioned": article.companies_mentioned
                        },
                        "alert": result.get("alert"),
                        "agent_analysis": result.get("agent_analysis"),
                        "enhanced": result.get("enhanced", False)
                    })

                    if result.get("alert"):
                        alerts_generated += 1
                        logger.info(f"  ✅ Alert generated!")
                    else:
                        logger.info(f"  ℹ️  No alert (below threshold)")
                else:
                    logger.info(f"  ℹ️  No result")

            except Exception as e:
                logger.error(f"  ❌ Error processing article: {str(e)}")
                # Continue with next article - article is already saved above
                continue

        logger.info(f"\n✅ Pipeline complete: {alerts_generated} alerts from {len(articles)} articles")

        return {
            "status": "success",
            "message": f"Processed {len(articles)} articles, generated {alerts_generated} alerts",
            "articles_fetched": len(articles),
            "alerts_generated": alerts_generated,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in fetch-and-analyze: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
