from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
import os
from datetime import datetime

from app.services.persistence import persistence_service
from app.services.stock_data import stock_data_service
from app.services.database import get_db_connection
from app.agents.workflow import app as langgraph_app

logger = logging.getLogger(__name__)

router = APIRouter()

# --- REQUEST MODELS ---
class AgentDiscoveryRequest(BaseModel):
    ticker: str

class WorkflowTriggerRequest(BaseModel):
    portfolio: List[str]
    user_id: str = "demo_user"

# --- SYSTEM & STATUS ---
@router.get("/health")
async def health_check():
    return {"status": "active", "version": "3.0.0", "engine": "LangGraph"}

# --- PORTFOLIO & MARKET ---
@router.get("/portfolio")
async def get_portfolio(user_name: Optional[str] = None):
    """Get user-specific portfolio from database."""
    try:
        from app.services.database import get_db_connection
        from app.services.auth import auth_service

        conn = get_db_connection()
        cursor = conn.cursor()

        # If user_name provided, get their specific portfolio
        if user_name:
            user = auth_service.get_or_create_user(user_name)
            user_id = user['id']
            cursor.execute("SELECT * FROM holdings WHERE user_id = ?", (user_id,))
        else:
            # Get most recent user's portfolio (fallback for backward compatibility)
            cursor.execute("SELECT * FROM holdings ORDER BY ROWID DESC LIMIT 10")

        holdings = cursor.fetchall()
        conn.close()

        if not holdings:
            return {"holdings": [], "timestamp": datetime.now().isoformat()}

        # Convert Row objects to dicts and enrich with live prices
        holdings = [dict(h) for h in holdings]
        tickers = [h['ticker'] for h in holdings]
        live_data = stock_data_service.get_live_prices(tickers)

        enriched = []
        for idx, h in enumerate(holdings):
            t = h['ticker']
            stock_info = live_data.get(t, {})
            price = stock_info.get('current_price', h.get('current_price', 0.0))
            avg_price = h.get('avg_price', 100.0)
            quantity = h.get('quantity', 10)
            
            # Check for invalid ticker flag
            is_valid = stock_info.get('is_valid', True)
            error_msg = stock_info.get('error', None)
            company_display = stock_info.get('company_name', h.get('company_name', t))

            enriched.append({
                "id": idx + 1,
                "ticker": t,
                "company": company_display,
                "quantity": quantity,
                "purchasePrice": avg_price,
                "currentPrice": price,
                "value": price * quantity,
                "gain_loss_pct": ((price - avg_price) / avg_price) * 100 if avg_price > 0 else 0,
                "is_valid": is_valid,
                "error": error_msg
            })


        return {"holdings": enriched, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in get_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/portfolio")
async def update_portfolio(request: Dict[str, Any], background_tasks: BackgroundTasks):
    """Update user-specific portfolio and trigger relationship discovery."""
    try:
        from app.services.database import get_db_connection
        from app.services.auth import auth_service
        from app.agents.nodes import agent_3b_discovery

        # Get or create user
        user_name = request.get("user_name", "User")
        user = auth_service.get_or_create_user(user_name)
        user_id = user['id']

        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Clear existing holdings for THIS USER ONLY
        cursor.execute("DELETE FROM holdings WHERE user_id = ?", (user_id,))

        # 2. Insert new holdings for this user
        holdings = request.get("portfolio", [])
        tickers = []
        for h in holdings:
            ticker = h['ticker']
            tickers.append(ticker)
            cursor.execute("""
                INSERT INTO holdings (ticker, company_name, quantity, avg_price, current_price, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ticker, h['company'], h.get('quantity', 10), h.get('purchase_price', 100.0),
                  h.get('purchase_price', 100.0), user_id))

            persistence_service.ensure_company_exists(ticker)

        conn.commit()
        conn.close()

        # 3. Trigger relationship discovery in background
        def discover_relationships():
            logger.info(f"🔍 Starting relationship discovery for user {user_name}: {len(tickers)} companies...")
            for ticker in tickers:
                try:
                    state = {"portfolio": tickers}
                    agent_3b_discovery(state)
                    logger.info(f"✅ Discovered relationships for {ticker}")
                except Exception as e:
                    logger.error(f"❌ Discovery failed for {ticker}: {e}")
            logger.info("🎉 Relationship discovery complete!")

        background_tasks.add_task(discover_relationships)

        # Create access token
        token = auth_service.create_access_token(user_id, user_name)

        return {
            "status": "success",
            "message": f"Updated portfolio with {len(holdings)} items for {user_name}",
            "tickers": tickers,
            "user_id": user_id,
            "token": token
        }
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/watchlist")
async def add_to_watchlist(request: Dict[str, Any]):
    """Add tickers to watchlist."""
    try:
        from app.services.database import get_db_connection
        
        tickers = request.get("tickers", [])
        if isinstance(tickers, str):
            tickers = [tickers]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # For now, just ensure companies exist in the database
        for ticker in tickers:
            persistence_service.ensure_company_exists(ticker)
        
        conn.close()
        
        return {"status": "success", "message": f"Added {len(tickers)} tickers to watchlist"}
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ALERTS & REASONING ---
@router.get("/alerts")
async def get_alerts(limit: int = 15):
    """Retrieve recent alerts with impact summary."""
    raw_alerts = persistence_service.get_alerts(limit)
    
    if not raw_alerts:
        return {"alerts": []}
    
    # Batch-fetch all reasoning trails at once to avoid N+1 queries
    conn = get_db_connection()
    cursor = conn.cursor()
    alert_ids = [alert['id'] for alert in raw_alerts]
    placeholders = ','.join(['?' for _ in alert_ids])
    cursor.execute(f"SELECT * FROM impact_analysis WHERE alert_id IN ({placeholders})", alert_ids)
    all_trails = cursor.fetchall()
    conn.close()
    
    # Group trails by alert_id
    trails_by_alert = {}
    for trail in all_trails:
        alert_id = trail['alert_id']
        if alert_id not in trails_by_alert:
            trails_by_alert[alert_id] = []
        trails_by_alert[alert_id].append(dict(trail))
    
    # Transform to frontend format
    enriched_alerts = []
    for alert in raw_alerts:
        reasoning_trail = trails_by_alert.get(alert['id'], [])
        
        # Build chain from reasoning trail
        chain = {}
        if reasoning_trail:
            if len(reasoning_trail) >= 1:
                chain['level1'] = reasoning_trail[0].get('reasoning', 'Event Trigger')[:100]
            if len(reasoning_trail) >= 2:
                chain['level2'] = reasoning_trail[1].get('reasoning', 'Intermediary Impact')[:100]
            if len(reasoning_trail) >= 3:
                chain['level3'] = reasoning_trail[2].get('reasoning', 'Portfolio Result')[:100]
        
        # Calculate average confidence from reasoning trail
        confidences = [step.get('confidence', 0.85) for step in reasoning_trail]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85
        
        # Build affected holdings from reasoning trail
        affected_holdings = []
        seen_tickers = set()
        for step in reasoning_trail:
            ticker = step.get('ticker')
            if ticker and ticker not in seen_tickers:
                seen_tickers.add(ticker)
                affected_holdings.append({
                    'company': ticker,
                    'ticker': ticker,
                    'impact_percent': alert.get('impact_pct', 0),
                    'impact_value': 0
                })
        
        enriched_alerts.append({
            'id': alert['id'],
            'title': alert.get('headline', 'Market Alert'),
            'severity': alert.get('severity', 'medium'),
            'impact_percent': alert.get('impact_pct', 0),
            'impact': alert.get('impact_pct', 0),
            'confidence': avg_confidence,
            'recommendation': 'MONITOR' if alert.get('severity') == 'low' else 'REVIEW',
            'chain': chain,
            'impactChain': chain,
            'affected_holdings': affected_holdings,
            'explanation': alert.get('full_reasoning', alert.get('ai_analysis', 'Analysis in progress...')),
            'description': alert.get('ai_analysis', ''),
            'sources': alert.get('source_urls', []),
            'tags': [alert.get('severity', 'alert')],
            'created_at': alert.get('created_at'),
            'timestamp': alert.get('created_at'),
            'icon': '⚠️' if alert.get('severity') == 'high' else '📊',
            'company': affected_holdings[0]['company'] if affected_holdings else 'Market',
            'ticker': affected_holdings[0]['ticker'] if affected_holdings else 'N/A'
        })
    
    return {"alerts": enriched_alerts}

@router.get("/alerts/{alert_id}")
async def get_alert_details(alert_id: str):
    """Get full reasoning trail for a specific alert."""
    details = persistence_service.get_alert_details(alert_id)
    if not details:
        raise HTTPException(status_code=404, detail="Alert not found")
    return details

# --- AGENTIC WORKFLOW & DISCOVERY ---
@router.post("/run-intelligence")
async def run_intelligence(request: WorkflowTriggerRequest):
    """Trigger the 6-agent LangGraph workflow."""
    try:
        initial_state = {
            "user_id": request.user_id,
            "portfolio": request.portfolio,
            "loop_count": 0,
            "news_articles": [],
            "errors": [],
            "workflow_status": "Started",
            "started_at": datetime.now().isoformat()
        }
        
        # Execute workflow
        final_state = langgraph_app.invoke(initial_state)
        
        return {
            "status": "complete",
            "alert_created": final_state.get("alert_created", False),
            "alert_id": final_state.get("alert_id"),
            "impact": final_state.get("portfolio_total_impact"),
            # Full State Details for Frontend Dashboard
            "news": final_state.get("news_articles", []),
            "classified_articles": final_state.get("classified_articles", []),
            "stock_impacts": final_state.get("stock_impacts", []),
            "discovered_relationships": final_state.get("discovered_relationships", []),
            "confidence": final_state.get("confidence_score", 0.0),
            "loop_count": final_state.get("loop_count", 0),
            "validation_decision": final_state.get("validation_decision"),
            "processing_time_ms": int((datetime.now() - datetime.fromisoformat(initial_state["started_at"])).total_seconds() * 1000)
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/graph/build")
async def get_supply_chain_graph(ticker: str):
    """Get relationship graph data for D3.js visualization."""
    rels = persistence_service.get_cached_relationships(ticker)
    # Format for D3
    nodes = [{"id": ticker, "type": "target"}]
    links = []
    for r in rels:
        nodes.append({"id": r['related_company'], "type": r['type']})
        links.append({"source": ticker, "target": r['related_company'], "type": r['type']})
        
    return {"nodes": nodes, "links": links}

@router.post("/relationships/discover")
async def discover_relationships(request: AgentDiscoveryRequest):
    """Force Agent 3B to discover relationships for a specific ticker."""
    from app.services.sec_parser import sec_parser
    from app.services.relationship_fusion import relationship_fusion
    
    try:
        # SEC Discovery
        sec_rels = sec_parser.extract_relationships(request.ticker)
        # Fallback/Fusion Logic
        fused = relationship_fusion.fuse(sec_rels)
        # Persistence
        persistence_service.save_discovered_relationships(request.ticker, fused)
        
        return {"status": "success", "fused_count": len(fused), "relationships": fused}
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/stats")
async def get_stats():
    """Get dashboard statistics."""
    return persistence_service.get_stats()

@router.get("/articles")
async def get_articles(limit: int = 15, portfolio: str = None):
    """
    Get LIVE news from MULTIPLE sources (NewsAPI, Finnhub, GNews, RSS, etc.)
    This endpoint ONLY fetches and displays live news - does NOT store in database.
    """
    from app.services.news_aggregator import NewsIngestionLayer
    
    # tickers = ['AAPL', 'NVDA', 'AMD', 'MSFT', 'GOOGL'] <--- REMOVED HARDCODED DEFAULT
    
    if portfolio:
        tickers = [t.strip().upper() for t in portfolio.split(',')]
    else:
        # Get from database if no portfolio param provided
        from app.services.database import get_db_connection
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker FROM holdings")
            holdings = cursor.fetchall()
            tickers = [h[0] for h in holdings] if holdings else []
            conn.close()
        except Exception as e:
            logger.error(f"Error fetching portfolio from DB: {e}")
            tickers = []
    
    if not tickers:
        logger.info("No tickers to fetch news for (Empty Portfolio)")
        return []

    
    logger.info(f"📰 Fetching LIVE news from MULTIPLE sources for: {tickers} (NO DATABASE STORAGE)")
    
    try:
        news_layer = NewsIngestionLayer()
        query = " OR ".join(tickers)
        
        # Fetch from ALL available sources - LIVE DATA ONLY
        all_articles = []
        
        # 1. RSS Feeds (Unlimited, always available)
        all_articles.extend(news_layer.fetch_rss_feeds(tickers) or [])
        all_articles.extend(news_layer.fetch_google_news_rss(query) or [])
        
        # 2. Official APIs
        all_articles.extend(news_layer.fetch_news_api(query) or [])
        all_articles.extend(news_layer.fetch_newsdata(query) or [])
        all_articles.extend(news_layer.fetch_finnhub(query) or [])
        all_articles.extend(news_layer.fetch_gnews(query) or [])
        all_articles.extend(news_layer.fetch_hacker_news() or [])
        
        logger.info(f"✅ Got {len(all_articles)} LIVE articles from all sources")
        
        # Filter by date (last 7 days)
        from datetime import datetime, timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        recent_articles = []
        for art in all_articles:
            pub_date_str = art.get('published_at', '')
            if pub_date_str:
                try:
                    # Parse ISO date
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    if pub_date >= cutoff_date:
                        recent_articles.append(art)
                except:
                    # If date parsing fails, include it anyway (might be recent)
                    recent_articles.append(art)
            else:
                # If no date, assume recent and include
                recent_articles.append(art)
        
        logger.info(f"📅 Filtered to {len(recent_articles)} articles from last 7 days")
        
        # Filter by portfolio companies and tag
        filtered = []
        for art in recent_articles:
            text = f"{art.get('title', '')} {art.get('content', '')}".upper()
            affected = [t for t in tickers if t in text]
            if affected:
                art['affected_companies'] = affected
                filtered.append(art)
        
        # If no portfolio matches, still return recent articles (broader market news)
        if not filtered and recent_articles:
            filtered = recent_articles[:limit * 2]  # Get more to filter from
        
        # Deduplicate by URL
        seen = set()
        unique = []
        for a in filtered:
            url = a.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(a)
        
        # Sort by published date (newest first)
        unique.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        # Return live articles only - NO STATIC FALLBACK
        result = unique[:limit]
        logger.info(f"📊 Returning {len(result)} LIVE articles (not stored in database)")
        return {"articles": result}
        
    except Exception as e:
        logger.error(f"❌ News fetch error: {e}")
        # Return empty array instead of static data
        return {"articles": []}
@router.get("/relationships")
async def get_relationships(limit: int = 100):
    """Get all discovered relationships."""
    return persistence_service.get_all_relationships(limit)

@router.get("/knowledge-graphs")
async def get_knowledge_graphs():
    """Get knowledge graph data (Alias to relationships for now)."""
    # This might expect a different format, but we'll start with relationships
    return persistence_service.get_all_relationships(limit=50)

@router.get("/news/fetch-status")
async def get_news_fetch_status():
    """Get status of background news fetching."""
    # Since we use background tasks, we'll simulate an 'idle' or 'active' state
    # In a real app, we'd check a task queue or database flag
    return {"status": "idle", "last_fetch": datetime.now().isoformat(), "message": "Ready"}

@router.post("/fetch-news")
async def trigger_news_fetch(background_tasks: BackgroundTasks):
    """Trigger manual news fetch (simulated by running pipeline)."""
    # For now, we'll just trigger the full pipeline in background
    # Get portfolio from database
    from app.services.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ticker FROM holdings')
    holdings = cursor.fetchall()
    conn.close()
    portfolio = [h[0] for h in holdings] if holdings else []
    if not portfolio:
        return {'status': 'error', 'message': 'No portfolio found'}
    req = WorkflowTriggerRequest(portfolio=portfolio)
    background_tasks.add_task(run_intelligence, req)
    return {"status": "started", "message": "News fetch and analysis triggered"}

@router.post("/run-pipeline")
async def run_pipeline(background_tasks: BackgroundTasks):
    """Trigger the full analysis pipeline for current portfolio."""
    from app.services.database import get_db_connection

    # Get portfolio from database (NO STATIC DATA)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM holdings")
    portfolio = [row['ticker'] for row in cursor.fetchall()]
    conn.close()

    if not portfolio:
        raise HTTPException(status_code=400, detail="No portfolio found. Please add companies first.")

    req = WorkflowTriggerRequest(portfolio=portfolio)
    background_tasks.add_task(run_intelligence, req)
    return {"status": "started", "message": f"Pipeline execution started for {len(portfolio)} companies"}

@router.get("/stock-prices")
async def get_stock_prices(tickers: Optional[str] = None):
    """Get live stock prices."""
    if not tickers:
        # Default to portfolio
        # Get from database
        from app.services.database import get_db_connection
        conn = get_db_connection()

        cursor = conn.cursor()
        cursor.execute('SELECT ticker FROM holdings')
        symbol_list = [h[0] for h in cursor.fetchall()]
        conn.close()
    else:
        symbol_list = tickers.split(",")
        
    return stock_data_service.get_live_prices(symbol_list)
@router.post("/analyze-news-for-alerts")
async def analyze_news_for_alerts(background_tasks: BackgroundTasks):
    """Analyze current news articles and generate alerts for portfolio impacts."""
    
    def generate_alerts_from_news():
        """Background task to analyze news and create alerts"""
        try:
            from app.services.gemini_client import GeminiClient
            from app.services.database import get_db_connection
            import uuid
            
            logger.info("🔍 Starting news analysis for alert generation...")
            
            # Get portfolio
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, company_name FROM holdings")
            portfolio = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not portfolio:
                logger.warning("No portfolio found, skipping alert generation")
                return
            
            # Get recent articles (from our multi-source feed)
            from app.services.news_aggregator import NewsIngestionLayer
            news_layer = NewsIngestionLayer()
            tickers = [p['ticker'] for p in portfolio]
            query = " OR ".join(tickers)
            
            articles = []
            articles.extend(news_layer.fetch_news_api(query) or [])
            articles.extend(news_layer.fetch_finnhub(query) or [])
            
            logger.info(f"📰 Analyzing {len(articles)} articles for portfolio impact...")
            
            # Analyze each article using the sophisticated 7-Stage Pipeline
            from app.services.pipeline import Pipeline
            from app.models.article import Article
            from datetime import datetime
            
            pipeline = Pipeline()
            alerts_generated = 0
            
            for article_data in articles[:5]:  # Limit to 5 most recent
                try:
                    # Convert to Article model
                    article_obj = Article(
                        title=article_data.get('title', 'Unknown'),
                        url=article_data.get('url', 'http://unknown.com'),
                        source=article_data.get('source', 'Unknown'),
                        published_at=datetime.now(), # Default to now if missing
                        content=article_data.get('content') or article_data.get('description', ''),
                        companies_mentioned=[]
                    )
                    
                    # Execute Pipeline (Validates -> Extracts Relations -> Infers Cascade -> Calculates Impact -> Saves Alert)
                    logger.info(f"🚀 Pipeline executing for: {article_obj.title[:50]}...")
                    alert = pipeline.process_article(article_obj)
                    
                    if alert:
                        alerts_generated += 1
                        logger.info(f"✅ Generated alert: {alert.id}")
                    else:
                        logger.info(f"⏭️ No alert generated for article (Filtered/Low Confidence)")
                        
                except Exception as e:
                    logger.error(f"Error processing article in pipeline: {e}")
                    continue
            
            logger.info(f"🎉 Alert generation complete! Created {alerts_generated} alerts")
            
        except Exception as e:
            logger.error(f"❌ Alert generation failed: {e}")
    
    # Run in background
    background_tasks.add_task(generate_alerts_from_news)
    
    return {
        "status": "started",
        "message": "Analyzing news articles for portfolio impacts in background..."
    }
