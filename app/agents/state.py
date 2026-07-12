from typing import TypedDict, List, Dict, Optional

class SupplyChainState(TypedDict):
    # ===== INPUTS =====
    user_id: str
    portfolio: List[str]

    # ===== LANGCHAIN MEMORY CONTEXT =====
    # Assembled by build_user_context() before the pipeline starts.
    # Injected as a system-level prefix into every agent's LLM prompt.
    user_context: str            # full profile + session memory + entity memory string
    agent_memory: Dict           # raw ticker entity memories {ticker: {...}}

    # ===== AGENT 1 OUTPUT =====
    news_articles: List[Dict]
    last_fetch_time: str

    # ===== AGENT 2 OUTPUT =====
    classified_articles: List[Dict]
    high_priority_articles: List[str]

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
    validation_decision: str
    gaps_identified: List[str]
    refined_search_queries: List[str]
    loop_count: int

    # ===== AGENT 6 OUTPUT =====
    alert_created: bool
    alert_id: str

    # ===== AGENT 2B OUTPUT (Alpha Scorer) =====
    alpha_score_total: float
    alpha_signal: str
    alpha_details: List[str]
    alpha_convergence_signals: List[str]

    # ===== AGENT 2C OUTPUT (Convergence Detector) =====
    convergence_zones: List[Dict]
    converged_signals_count: int
    confidence_boost: float
    regime_factor_allocation: Dict

    # ===== ML / REGIME =====
    market_regime: str   # "bull" | "bear" | "sideways" | "volatile"

    # ===== METADATA =====
    workflow_status: str
    errors: List[str]
    started_at: str
    completed_at: str
    processing_time: float
