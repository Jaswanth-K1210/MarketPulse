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
    """Get current portfolio"""
    try:
        portfolio_data = database.get_portfolio()
        if not portfolio_data:
            # Return default portfolio
            from app.config import DEFAULT_PORTFOLIO
            portfolio_data = {"user_name": "Jaswanth", "portfolio": DEFAULT_PORTFOLIO}

        # Get current values
        portfolio_value = market_data_service.get_portfolio_value(
            portfolio_data.get('portfolio', [])
        )

        return {
            "user_name": portfolio_data.get('user_name'),
            "holdings": portfolio_data.get('portfolio'),
            "current_value": portfolio_value
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
    severity: Optional[str] = None
):
    """Get recent alerts"""
    try:
        if severity:
            alerts = database.get_alerts_by_severity(severity, limit)
        else:
            alerts = database.get_all_alerts(limit)

        return {
            "count": len(alerts),
            "alerts": [alert.to_dict() for alert in alerts]
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_articles(limit: int = 20):
    """Get recent articles"""
    try:
        articles = database.get_all_articles(limit)
        return {
            "count": len(articles),
            "articles": [article.to_dict() for article in articles]
        }
    except Exception as e:
        logger.error(f"Error getting articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
