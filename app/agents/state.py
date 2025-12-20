from typing import TypedDict, List, Dict, Union, Optional

class SupplyChainState(TypedDict):
    # ===== INPUTS =====
    user_id: str
    portfolio: List[str]  # ["AAPL", "NVDA", "MSFT"]
    
    # ===== AGENT 1 OUTPUT =====
    news_articles: List[Dict]
    last_fetch_time: str
    
    # ===== AGENT 2 OUTPUT =====
    classified_articles: List[Dict]
    high_priority_articles: List[str]  # article IDs
    
    # ===== AGENT 3A/3B OUTPUT =====
    matched_stocks: List[Dict]
    relationship_data: Dict
    cache_hits: List[str]
    cache_misses: List[str]
    discovered_relationships: List[Dict]
    
    # ===== AGENT 4 OUTPUT =====
    impact_analysis: Dict
    stock_impacts: List[Dict]
    portfolio_total_impact: Dict
    
    # ===== AGENT 5 OUTPUT =====
    confidence_score: float
    validation_decision: str  # "ACCEPT" or "REQUEST_MORE_DATA"
    gaps_identified: List[str]
    refined_search_queries: List[str]
    loop_count: int
    
    # ===== AGENT 6 OUTPUT =====
    alert_created: bool
    alert_id: str
    
    # ===== METADATA =====
    workflow_status: str
    errors: List[str]
    started_at: str
    completed_at: str
    processing_time: float
