from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime

from app.services.persistence import persistence_service
from app.services.stock_data import stock_data_service
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
async def get_portfolio():
    """Get Jaswanth's portfolio from SQLite."""
    try:
        from app.services.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM holdings")
        holdings = cursor.fetchall()
        conn.close()
        
        # Enrich with live prices
        tickers = [h['ticker'] for h in holdings]
        live_data = stock_data_service.get_live_prices(tickers)
        
        enriched = []
        for h in holdings:
            t = h['ticker']
            price = live_data.get(t, {}).get('current_price', h['current_price'])
            enriched.append({
                "ticker": t,
                "quantity": h['quantity'],
                "avg_price": h['avg_price'],
                "current_price": price,
                "value": price * h['quantity'],
                "gain_loss_pct": ((price - h['avg_price']) / h['avg_price']) * 100
            })
            
        return {"holdings": enriched, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error in get_portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ALERTS & REASONING ---
@router.get("/alerts")
async def get_alerts(limit: int = 15):
    """Retrieve recent alerts with impact summary."""
    return {"alerts": persistence_service.get_alerts(limit)}

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
