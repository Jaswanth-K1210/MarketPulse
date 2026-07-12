from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
import logging
import os
from datetime import datetime

from app.services.persistence import persistence_service
from app.services.stock_data import stock_data_service
from app.services.database import get_db_connection
from app.agents.workflow import app as langgraph_app

logger = logging.getLogger(__name__)

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

# --- REQUEST MODELS ---
class AgentDiscoveryRequest(BaseModel):
    ticker: str

class WorkflowTriggerRequest(BaseModel):
    portfolio: List[str]
    user_id: str = "demo_user"

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class GoogleAuthRequest(BaseModel):
    access_token: str  # Google access token from @react-oauth/google implicit flow

# --- SYSTEM & STATUS ---
@router.get("/health")
async def health_check():
    from app.ml.llm_router import llm_router
    from app.services.news_aggregator import news_aggregator_layer
    return {
        "status": "active",
        "version": "3.0.0",
        "engine": "LangGraph",
        "llm": llm_router.health(),
        "news": news_aggregator_layer.source_stats(),
    }

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
    """Trigger the 6-agent LangGraph workflow with personalised user context."""
    try:
        # ── Build LangChain-style user context from MongoDB ──────────────────
        user_context = ""
        agent_memory: Dict[str, Any] = {}
        try:
            from app.db.agent_memory import build_user_context, get_ticker_memories
            from app.db.user_profile import get_by_username
            user_doc = await get_by_username(request.user_id) or {}
            user_context = await build_user_context(
                user_id=request.user_id,
                username=request.user_id,
                portfolio=request.portfolio,
                risk_tolerance=user_doc.get("risk_tolerance", "moderate"),
                alert_threshold=user_doc.get("alert_threshold", 0.05),
                preferred_sectors=user_doc.get("preferred_sectors", []),
            )
            agent_memory = await get_ticker_memories(request.user_id, request.portfolio)
            logger.info(f"🧠 User context loaded for {request.user_id}: {len(user_context)} chars, "
                        f"{len(agent_memory)} ticker memories")
        except Exception as mem_err:
            logger.warning(f"Could not load user context (MongoDB may be offline): {mem_err}")

        initial_state = {
            "user_id": request.user_id,
            "portfolio": request.portfolio,
            "user_context": user_context,
            "agent_memory": agent_memory,
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
    Return news articles — DB cache first, live RSS fetch as background refresh.
    """
    from app.services.database import get_db_connection

    # ── 1. Always try DB cache first (fast, reliable) ─────────────────────────
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, url, source, content, published_at FROM articles ORDER BY published_at DESC LIMIT ?",
            (limit,)
        )
        db_rows = cursor.fetchall()
        conn.close()
        if db_rows:
            articles = [
                {
                    "title":        r[0] or "",
                    "url":          r[1] or "",
                    "source":       r[2] or "Source",
                    "content":      r[3] or "",
                    "published_at": r[4] or "",
                    "tickers":      [],
                }
                for r in db_rows
            ]
            # Tag articles with tickers mentioned in title/content
            if portfolio:
                watch = [t.strip().upper() for t in portfolio.split(',')]
            else:
                watch = ['AAPL','NVDA','AMD','INTC','TSM','MSFT','GOOGL','META','AMZN']
            for art in articles:
                text = f"{art['title']} {art['content']}".upper()
                art['tickers'] = [t for t in watch if t in text]
            logger.info(f"📰 Returning {len(articles)} cached articles from DB")
            return {"articles": articles}
    except Exception as e:
        logger.warning(f"DB article fetch failed: {e}")

    # ── 2. Fallback: live fetch (best-effort, non-blocking) ───────────────────
    if portfolio:
        tickers = [t.strip().upper() for t in portfolio.split(',')]
    else:
        tickers = ['AAPL', 'NVDA', 'AMD', 'INTC', 'TSM']

    if not tickers:
        return {"articles": []}

    
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
                except ValueError:
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
    """
    Get live stock prices.
    Uses Alpaca (real-time) when keys are configured; falls back to yfinance.
    """
    from app.services.alpaca_service import alpaca_service

    if tickers:
        symbol_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    else:
        from app.services.database import get_db_connection
        conn    = get_db_connection()
        cursor  = conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM holdings")
        symbol_list = [h[0] for h in cursor.fetchall()]
        conn.close()

    if not symbol_list:
        return {"data": {}, "source": "none"}

    # ── Alpaca path (fast, real-time) ──────────────────────────────────────
    if alpaca_service.available:
        data = alpaca_service.get_snapshots(symbol_list)
        if data:
            logger.info("Stock prices served via Alpaca for %d tickers", len(data))
            return {"data": data, "source": "alpaca"}

    # ── yfinance fallback ──────────────────────────────────────────────────
    prices = stock_data_service.get_live_prices(symbol_list)
    return {"data": prices, "source": "yfinance"}
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


# ── AUTH ENDPOINTS ────────────────────────────────────────────────────────────

@router.post("/auth/register")
async def register(req: RegisterRequest):
    """Create a new user account (MongoDB primary, SQLite fallback)."""
    from app.services.auth import register_user, make_token
    try:
        user = await register_user(req.username, req.password, req.email)
        token = make_token(user["id"], user["username"])
        return {
            "token": token,
            "user": {"id": user["id"], "username": user["username"], "email": user.get("email")},
            "message": "Account created successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("register error: %s", e)
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/auth/login")
async def login(req: LoginRequest):
    """Authenticate and return a JWT (MongoDB primary, SQLite fallback)."""
    from app.services.auth import login_user, make_token
    user = await login_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = make_token(user["id"], user["username"])
    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "email": user.get("email")},
        "message": "Login successful",
    }


@router.get("/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Return the currently authenticated user from their JWT token."""
    from app.services.auth import verify_token
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    return {"user_id": payload["user_id"], "username": payload["username"]}


@router.post("/auth/google")
async def google_auth(req: GoogleAuthRequest):
    """
    Accept a Google OAuth access_token, fetch Google user info,
    then find-or-create the user in MongoDB (or SQLite fallback).
    """
    import aiohttp
    from app.services.auth import google_login, make_token

    if not os.getenv("GOOGLE_CLIENT_ID"):
        raise HTTPException(status_code=501, detail="Google OAuth not configured — set GOOGLE_CLIENT_ID")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {req.access_token}"},
        ) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=401, detail="Invalid Google access token")
            idinfo = await resp.json()

    google_sub   = idinfo.get("sub", "")
    google_email = idinfo.get("email", "")
    google_name  = idinfo.get("name") or idinfo.get("given_name") or google_email.split("@")[0]

    user = await google_login(google_sub, google_email, google_name)
    token = make_token(user["id"], user["username"])
    return {
        "token": token,
        "user": {"id": user["id"], "username": user["username"], "email": user.get("email")},
        "message": "Google sign-in successful",
    }


# ── ML Intelligence endpoints ─────────────────────────────────────────────────

class MonteCarloRequest(BaseModel):
    portfolio: List[str]
    shocked_ticker: str
    shock_score: float        # FinBERT score -1..+1
    risk_threshold: float = -2.0

@router.post("/intelligence/supply-chain-shock")
async def supply_chain_shock(req: MonteCarloRequest):
    """
    Run GNN shock propagation + Monte Carlo simulation for a given news event.
    Returns per-ticker portfolio impact and full 48-hour risk distribution.
    """
    from app.services.gnn_service       import get_portfolio_impact
    from app.services.monte_carlo_service import monte_carlo
    from app.services.alpaca_service    import alpaca_service

    # GNN propagation
    gnn = get_portfolio_impact(req.portfolio, req.shocked_ticker, req.shock_score)

    # Fetch live prices
    current_prices: dict = {}
    if req.portfolio:
        snaps = alpaca_service.get_snapshots(req.portfolio) if alpaca_service.available else {}
        current_prices = {t: v["current_price"] for t, v in snaps.items() if v.get("is_valid")}

    # Monte Carlo
    mc = monte_carlo.simulate(
        portfolio=req.portfolio,
        gnn_impacts=gnn["portfolio_impacts"],
        current_prices=current_prices,
        risk_threshold=req.risk_threshold,
    )

    return {"gnn": gnn, "monte_carlo": mc}


@router.get("/intelligence/supply-chain/{ticker}")
async def get_supply_chain(ticker: str):
    """Return the direct supply-chain neighbours for a given ticker."""
    from app.services.gnn_service import get_supply_chain_neighbours
    return get_supply_chain_neighbours(ticker.upper())


@router.post("/intelligence/stress-test")
async def stress_test(portfolio: List[str]):
    """Run all predefined geopolitical stress scenarios against a portfolio."""
    from app.services.monte_carlo_service import monte_carlo, STRESS_SCENARIOS
    from app.services.alpaca_service import alpaca_service

    snaps = alpaca_service.get_snapshots(portfolio) if alpaca_service.available else {}
    prices = {t: v["current_price"] for t, v in snaps.items() if v.get("is_valid")}

    return monte_carlo.stress_test(portfolio, STRESS_SCENARIOS, prices)


@router.get("/intelligence/finbert-status")
async def finbert_status():
    """Check if FinBERT model is loaded and ready."""
    from app.services.finbert_service import finbert
    sample = finbert.score("TSMC halts production due to earthquake")
    return {
        "ready":  finbert.ready,
        "source": sample.get("source"),
        "sample": sample,
    }


@router.post("/fetch-and-analyze")
async def fetch_and_analyze(limit: int = 10):
    """
    Full pipeline: fetch recent news → FinBERT sentiment → GNN shock propagation
    → Monte Carlo 48h simulation.  Returns structured results for the Dashboard.
    """
    from app.services.finbert_service     import finbert
    from app.services.gnn_service         import get_portfolio_impact
    from app.services.monte_carlo_service import monte_carlo
    from app.services.alpaca_service      import alpaca_service
    from app.services.database            import get_db_connection
    import time

    started = time.time()

    # ── 1. Portfolio ──────────────────────────────────────────────────────────
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM holdings LIMIT 20")
    portfolio = [row[0] for row in cursor.fetchall()]
    cursor.execute(
        "SELECT id, title, content, source, published_at, tickers FROM articles ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows     = cursor.fetchall()
    conn.close()

    articles_out = []
    for r in rows:
        tickers_field = r[5] or ""
        articles_out.append({
            "id":           r[0],
            "title":        r[1],
            "content":      (r[2] or "")[:300],
            "source":       r[3],
            "published_at": r[4],
            "tickers":      [t.strip() for t in tickers_field.split(",") if t.strip()],
        })

    # ── 2. FinBERT: score each article headline ───────────────────────────────
    headlines = [a["title"] for a in articles_out if a["title"]]
    sentiments = finbert.score_batch(headlines) if headlines else []
    for i, a in enumerate(articles_out):
        a["sentiment"] = sentiments[i] if i < len(sentiments) else {}

    # ── 3. Pick top-impact article for GNN shock ──────────────────────────────
    gnn_result   = None
    mc_result    = None
    shocked_ticker = None
    if articles_out and portfolio:
        # Find the article with the most extreme sentiment that names a portfolio ticker
        best_article = None
        best_score   = 0.0
        for a in articles_out:
            s = a["sentiment"].get("score", 0.0)
            tickers_in_art = [t for t in a.get("tickers", []) if t in portfolio]
            if abs(s) > abs(best_score) and tickers_in_art:
                best_score   = s
                shocked_ticker = tickers_in_art[0]
                best_article = a

        if not shocked_ticker and articles_out:
            # Fallback: use first article's tickers or first portfolio ticker
            for a in articles_out:
                if a.get("tickers"):
                    shocked_ticker = a["tickers"][0]
                    best_score     = a["sentiment"].get("score", -0.2)
                    break
            if not shocked_ticker:
                shocked_ticker = portfolio[0]
                best_score     = -0.2

        # GNN propagation
        gnn_result = get_portfolio_impact(portfolio, shocked_ticker, best_score)

        # Live prices for MC
        current_prices: dict = {}
        snaps = alpaca_service.get_snapshots(portfolio) if alpaca_service.available else {}
        current_prices = {t: v["current_price"] for t, v in snaps.items() if v.get("is_valid")}

        mc_result = monte_carlo.simulate(
            portfolio=portfolio,
            gnn_impacts=gnn_result["portfolio_impacts"],
            current_prices=current_prices,
        )

    elapsed_ms = int((time.time() - started) * 1000)

    port_mc = (mc_result or {}).get("portfolio", {})

    return {
        "status":            "complete",
        "articles_fetched":  len(articles_out),
        "alerts_generated":  len([a for a in articles_out if abs(a["sentiment"].get("score", 0)) > 0.3]),
        "articles":          articles_out,
        "shocked_ticker":    shocked_ticker,
        "gnn":               gnn_result,
        "monte_carlo":       mc_result,
        # Convenience flat fields for the Dashboard summary card
        "var_95":            round(port_mc.get("var_95_pct",   0), 2),
        "cvar_95":           round(port_mc.get("cvar_95_pct",  0), 2),
        "prob_loss":         round(port_mc.get("prob_loss",    0) * 100, 1),
        "mc_severity":       port_mc.get("severity", "LOW"),
        "avg_gnn_impact":    round((gnn_result or {}).get("avg_portfolio_impact", 0), 2),
        "processing_ms":     elapsed_ms,
    }
