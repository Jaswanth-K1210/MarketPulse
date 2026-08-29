from typing import Any, TypedDict, List, Dict, Optional

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

    # ===== QUANT TOOL DISPATCHER OUTPUT =====
    # Structured output from all quantitative tools (technical, options, insider, etc.)
    quant_tool_data: Dict[str, Dict]          # {ticker: {technical: {...}, options_flow: {...}, ...}}
    quant_tool_summaries: List[str]           # Per-ticker LLM-ready summaries
    quant_tools_dispatched: bool              # Whether tools were dispatched this run

    # ===== AGENT 2B OUTPUT (Alpha Scorer) =====
    alpha_score_total: float
    alpha_signal: str
    alpha_details: List[str]
    alpha_convergence_signals: List[str]
    alpha_llm_synthesis: str                  # LLM synthesis of tool outputs (for audit)

    # ===== AGENT 2C OUTPUT (Convergence Detector) =====
    convergence_zones: List[Dict]
    converged_signals_count: int
    confidence_boost: float
    regime_factor_allocation: Dict
    correlation_signals: List[Dict]           # From correlation engine

    # ===== ML / REGIME =====
    market_regime: str   # "bull" | "bear" | "sideways" | "volatile"

    # ===== MEMORY AGENT OUTPUT =====
    temporal_context: Dict[str, str]           # {ticker: temporal_context_string}
    memory_signals_recorded: bool              # Whether signals were recorded to Redis

    # ===== KNOWLEDGE GRAPH OUTPUT =====
    kg_context: Dict[str, Any]                 # {ticker: kg_retrieval_result}
    kg_entities_found: int                     # Total entities found across all tickers

    # ===== QUALITY EVALUATOR OUTPUT =====
    quality_scores: Dict[str, Any]             # AnalyScore 5-dimension evaluation
    quality_grade: str                         # A/B/C/D/F

    # ===== AUDIT OUTPUT =====
    audit_summary: Dict[str, Any]              # Full pipeline audit trail
    pipeline_id: str                           # Unique pipeline run identifier

    # ===== METADATA =====
    workflow_status: str
    errors: List[str]
    started_at: str
    completed_at: str
    processing_time: float
