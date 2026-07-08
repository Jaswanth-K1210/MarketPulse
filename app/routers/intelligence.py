"""
Intelligence API Router — risk scores, signals, correlations, macro, market overview, conflict.
All endpoints are cached and return bootstrap data on failure — never a 500.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.services.infrastructure.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bootstrap(key: str):
    """Return bootstrap seed value for key, or empty dict."""
    cache = get_cache_manager()
    return cache.bootstrap.get(key, {})


# ── Risk Scores ─────────────────────────────────────────────────────────────

@router.get("/risk-scores")
async def get_risk_scores(
    countries: Optional[str] = Query(None, description="Comma-separated country codes e.g. US,CN,TW"),
):
    cache = get_cache_manager()

    async def fetch():
        try:
            from app.services.intelligence.risk_scoring import RiskScoringEngine
            from app.services.data.conflict_data import ConflictDataService
            conflict_svc = ConflictDataService()
            engine = RiskScoringEngine()
            snapshot = await conflict_svc.get_conflict_snapshot()
            country_list = [c.strip().upper() for c in countries.split(",")] if countries else None
            scores_dict = engine.calculate_batch(
                acled_by_country=snapshot.get("acled_by_country", {}),
                ucdp_conflicts=snapshot.get("ucdp_conflicts", []),
                country_codes=country_list,
            )
            # Serialize RiskScore dataclass objects → plain dicts, sorted by score desc
            scores_list = sorted(
                [
                    {
                        "country_code": v.country_code if hasattr(v, "country_code") else k,
                        "country_name": getattr(v, "country_name", k),
                        "score": round(getattr(v, "score", 0), 1),
                    }
                    for k, v in scores_dict.items()
                ],
                key=lambda x: x["score"],
                reverse=True,
            )
            return {"status": "live", "scores": scores_list, "timestamp": _now()}
        except Exception as e:
            logger.warning("risk-scores fetch failed: %s", e)
            return None

    cache_key = f"risk_scores:{countries or 'all'}"
    result = await cache.get_or_fetch(cache_key, fetch, data_type="risk_scores")
    data = result.data if result.data else _bootstrap("risk_scores:all")
    if not data:
        data = {"status": "bootstrap", "scores": [], "timestamp": _now()}
    data["cache_source"] = getattr(result, "source", "bootstrap") if result else "bootstrap"
    return data


# ── Signals ─────────────────────────────────────────────────────────────────

@router.get("/signals")
async def get_signals():
    cache = get_cache_manager()

    async def fetch():
        try:
            from app.services.intelligence.signal_aggregator import SignalAggregator
            agg = SignalAggregator()
            signals = await agg.get_signals()
            return {"status": "live", "signals": signals, "total": len(signals), "timestamp": _now()}
        except Exception as e:
            logger.warning("signals fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch("signals:all", fetch, data_type="signals")
    data = result.data if result and result.data else None
    # Fall back to bootstrap if live signals list is empty
    if not data or not data.get("signals"):
        data = _bootstrap("signals:all") or {"status": "bootstrap", "signals": [], "timestamp": _now()}
    return data


# ── Correlations ─────────────────────────────────────────────────────────────

@router.get("/correlations")
async def get_correlations():
    cache = get_cache_manager()

    async def fetch():
        try:
            from app.services.intelligence.correlation_engine import CorrelationEngine
            engine = CorrelationEngine()
            correlations = await engine.detect_all()
            return {"status": "live", "correlations": correlations, "timestamp": _now()}
        except Exception as e:
            logger.warning("correlations fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch("correlations:all", fetch, data_type="signals")
    data = result.data if result and result.data else {"status": "bootstrap", "correlations": [], "timestamp": _now()}
    return data


# ── Macro ────────────────────────────────────────────────────────────────────

@router.get("/macro")
async def get_macro():
    cache = get_cache_manager()

    async def fetch():
        try:
            from app.services.data.macro_economic import MacroEconomicService
            svc = MacroEconomicService()
            data = await svc.get_snapshot()
            data["status"] = "live"
            data["timestamp"] = _now()
            return data
        except Exception as e:
            logger.warning("macro fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch("macro_snapshot", fetch, data_type="macro")
    data = result.data if result and result.data else _bootstrap("macro_snapshot")
    if not data:
        data = {"status": "bootstrap", "timestamp": _now()}
    return data


# ── Market Overview ──────────────────────────────────────────────────────────

@router.get("/market-overview")
async def get_market_overview():
    cache = get_cache_manager()

    async def fetch():
        try:
            from app.ml.regime_detector import regime_detector
            regime_data = regime_detector.detect()

            # Enrich with live index prices
            try:
                import yfinance as yf
                tickers = yf.download(["SPY", "QQQ", "^VIX"], period="5d", interval="1d",
                                      progress=False, auto_adjust=True, threads=False)
                closes = tickers["Close"].iloc[-1].to_dict() if not tickers.empty else {}
            except Exception:
                closes = {}

            return {
                "status": "live",
                "regime": regime_data.get("regime", "sideways"),
                "confidence": regime_data.get("confidence", 0.5),
                "spy_5d_return": regime_data.get("spy_5d_return"),
                "vix": regime_data.get("vix") or closes.get("^VIX"),
                "indices": {
                    "SPY": {"price": closes.get("SPY")},
                    "QQQ": {"price": closes.get("QQQ")},
                    "VIX": {"price": closes.get("^VIX")},
                },
                "timestamp": _now(),
            }
        except Exception as e:
            logger.warning("market-overview fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch("market_overview", fetch, data_type="market")
    data = result.data if result and result.data else _bootstrap("market_overview")
    if not data:
        data = {"status": "bootstrap", "regime": "sideways", "timestamp": _now()}
    return data


# ── Conflict ─────────────────────────────────────────────────────────────────

@router.get("/conflict")
async def get_conflict(
    days: int = Query(7, ge=1, le=30),
    country: Optional[str] = Query(None),
):
    cache = get_cache_manager()
    cache_key = f"conflict:{country or 'all'}:{days}"

    async def fetch():
        try:
            from app.services.data.conflict_data import ConflictDataService
            svc = ConflictDataService()
            data = await svc.get_conflict_snapshot(days=days, country_code=country)
            data["status"] = "live"
            data["timestamp"] = _now()
            return data
        except Exception as e:
            logger.warning("conflict fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="conflict")
    data = result.data if result and result.data else _bootstrap(f"conflict:all:{days}")
    if not data:
        data = {"status": "bootstrap", "active_conflicts": [], "timestamp": _now()}
    return data
