"""
LangChain-style per-user agent memory backed by MongoDB Atlas.

Architecture mirrors LangChain's ConversationSummaryBufferMemory pattern:
  - Entity memory   : what we know about each ticker for this user
  - Session summaries: compressed analysis results per run
  - Context builder : assembles a structured prompt prefix for LangGraph agents

When MongoDB is unavailable the module silently returns empty context,
so agents still function — just without personalised memory.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from app.db.mongo import is_available, memory_col, sessions_col

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Entity memory ─────────────────────────────────────────────────────────────

async def upsert_ticker_memory(
    user_id: str,
    ticker: str,
    findings: Dict[str, Any],
) -> None:
    """
    Store / update what the agents know about a specific ticker for this user.
    findings example:
        {
            "risk_score": 0.72,
            "trend": "rising",
            "last_event": "TSMC production halt",
            "impact_pct": -4.3,
            "regime": "volatile",
        }
    """
    if not is_available():
        return
    col = memory_col()
    await col.update_one(
        {"user_id": user_id, "ticker": ticker},
        {"$set": {**findings, "updated_at": _now()}},
        upsert=True,
    )


async def get_ticker_memories(user_id: str, tickers: List[str]) -> Dict[str, Dict]:
    """Return entity memories for the given tickers, keyed by ticker symbol."""
    if not is_available():
        return {}
    col = memory_col()
    cursor = col.find({"user_id": user_id, "ticker": {"$in": tickers}})
    result: Dict[str, Dict] = {}
    async for doc in cursor:
        t = doc.get("ticker", "")
        result[t] = {k: v for k, v in doc.items() if k not in ("_id", "user_id")}
    return result


# ── Session / analysis summaries ──────────────────────────────────────────────

async def save_analysis_session(
    user_id: str,
    portfolio: List[str],
    regime: str,
    alerts_generated: int,
    top_risks: List[Dict],
    summary_text: str,
) -> None:
    """Persist a compressed summary of one full pipeline run."""
    if not is_available():
        return
    col = sessions_col()
    await col.insert_one({
        "user_id": user_id,
        "portfolio": portfolio,
        "regime": regime,
        "alerts_generated": alerts_generated,
        "top_risks": top_risks[:5],   # store only top-5 to keep docs lean
        "summary": summary_text,
        "created_at": _now(),
    })


async def get_recent_sessions(user_id: str, limit: int = 3) -> List[Dict]:
    """Retrieve the N most recent analysis sessions for this user."""
    if not is_available():
        return []
    col = sessions_col()
    cursor = col.find(
        {"user_id": user_id},
        sort=[("created_at", -1)],
        limit=limit,
    )
    docs = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        docs.append(doc)
    return docs


# ── Context builder — the LangChain memory equivalent ─────────────────────────

async def build_user_context(
    user_id: str,
    username: str,
    portfolio: List[str],
    risk_tolerance: str = "moderate",
    alert_threshold: float = 0.05,
    preferred_sectors: Optional[List[str]] = None,
) -> str:
    """
    Assemble a structured natural-language context string to prepend to
    every LangGraph agent prompt.  Equivalent to LangChain's
    ConversationSummaryBufferMemory.load_memory_variables().

    Example output injected into agents:
        === USER INTELLIGENCE PROFILE ===
        User: jaswanth | Risk tolerance: moderate | Alert threshold: 5%
        Portfolio: AAPL, NVDA, TSMC, AMD (4 holdings)

        === PREVIOUS ANALYSIS MEMORY ===
        [2025-05-10] Regime: volatile | 3 alerts generated
          Top risks: TSMC (-4.3% impact, supply chain), NVDA (+2.1%, earnings beat)
          Summary: Semiconductor supply chain stress elevated due to Taiwan weather events.

        === TICKER ENTITY MEMORY ===
        AAPL   | risk: 0.45 | trend: stable  | last: "EU antitrust fine"
        NVDA   | risk: 0.61 | trend: rising  | last: "H100 demand surge"
        TSMC   | risk: 0.78 | trend: rising  | last: "Production halt"
        AMD    | risk: 0.38 | trend: stable  | last: "Market share gains"
    """
    lines: List[str] = []

    # --- User profile block ---
    sectors_str = ", ".join(preferred_sectors or []) or "all sectors"
    lines += [
        "=== USER INTELLIGENCE PROFILE ===",
        f"User: {username} | Risk tolerance: {risk_tolerance} | Alert threshold: {alert_threshold * 100:.0f}%",
        f"Portfolio: {', '.join(portfolio)} ({len(portfolio)} holdings) | Sectors: {sectors_str}",
        "",
    ]

    # --- Session memory block ---
    sessions = await get_recent_sessions(user_id, limit=3)
    if sessions:
        lines.append("=== PREVIOUS ANALYSIS MEMORY ===")
        for s in sessions:
            date = s.get("created_at", "")[:10]
            risks = "; ".join(
                f"{r.get('ticker','?')} ({r.get('impact_pct', 0):+.1f}%, {r.get('reason','')[:30]})"
                for r in s.get("top_risks", [])
            )
            lines.append(
                f"[{date}] Regime: {s.get('regime','?')} | {s.get('alerts_generated', 0)} alerts"
            )
            if risks:
                lines.append(f"  Top risks: {risks}")
            if s.get("summary"):
                lines.append(f"  Summary: {s['summary'][:200]}")
        lines.append("")

    # --- Ticker entity memory block ---
    memories = await get_ticker_memories(user_id, portfolio)
    if memories:
        lines.append("=== TICKER ENTITY MEMORY ===")
        for ticker in portfolio:
            m = memories.get(ticker)
            if m:
                lines.append(
                    f"{ticker:<6} | risk: {m.get('risk_score', 0):.2f}"
                    f" | trend: {m.get('trend', 'unknown'):<8}"
                    f" | last: \"{m.get('last_event', '')[:40]}\""
                )
        lines.append("")

    return "\n".join(lines)


async def extract_and_save_session_memory(
    user_id: str,
    state: Dict[str, Any],
) -> None:
    """
    Called after a pipeline run to compress + persist what was learned.
    Extracts key findings from LangGraph state and saves them to MongoDB.
    """
    if not is_available():
        return

    portfolio = state.get("portfolio", [])
    regime = state.get("market_regime", "unknown")
    stock_impacts = state.get("stock_impacts", [])
    alerts = state.get("alert_id")

    # Build top risks list from stock impacts
    top_risks = []
    for imp in sorted(stock_impacts, key=lambda x: abs(x.get("impact_percent", 0)), reverse=True)[:5]:
        top_risks.append({
            "ticker": imp.get("ticker"),
            "impact_pct": imp.get("impact_percent", 0),
            "reason": imp.get("reason", ""),
        })
        # Also update per-ticker entity memory
        await upsert_ticker_memory(user_id, imp.get("ticker", ""), {
            "risk_score": min(abs(imp.get("impact_percent", 0)) / 20, 1.0),
            "trend": "falling" if imp.get("impact_percent", 0) < 0 else "rising",
            "last_event": (imp.get("reason") or "")[:80],
            "impact_pct": imp.get("impact_percent", 0),
            "regime": regime,
        })

    # Summarise in one sentence using the portfolio total impact
    portfolio_impact = state.get("portfolio_total_impact", {})
    total_pct = portfolio_impact.get("total_impact_percent", 0.0)
    summary = (
        f"Portfolio {total_pct:+.1f}% net impact detected. "
        f"Regime: {regime}. "
        f"Top mover: {top_risks[0]['ticker'] if top_risks else 'none'}."
    )

    alerts_generated = 1 if alerts else 0

    await save_analysis_session(
        user_id=user_id,
        portfolio=portfolio,
        regime=regime,
        alerts_generated=alerts_generated,
        top_risks=top_risks,
        summary_text=summary,
    )
    logger.info(f"🧠 Agent memory saved for user {user_id} | session: {regime}, {alerts_generated} alerts")
