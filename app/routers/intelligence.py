"""
Intelligence API Router — risk scores, signals, correlations, macro, market overview, conflict, OSINT signals.
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


# ── OSINT: Insider Trades ────────────────────────────────────────────────────

@router.get("/insider-trades/{ticker}")
async def get_insider_trades(ticker: str):
    cache = get_cache_manager()
    cache_key = f"insider_trades:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.insider_trades import insider_trades_service
            data = await insider_trades_service.get_insider_trades(ticker)
            score = insider_trades_service.score_insider_activity(data)
            return {"status": "live", "ticker": ticker.upper(), "trades": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("insider-trades fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "trades": [], "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Short Interest ────────────────────────────────────────────────────

@router.get("/short-interest/{ticker}")
async def get_short_interest(ticker: str):
    cache = get_cache_manager()
    cache_key = f"short_interest:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.short_interest import short_interest_service
            data = await short_interest_service.get_short_interest(ticker)
            score = short_interest_service.score_short_interest(data)
            return {"status": "live", "ticker": ticker.upper(), "short_interest": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("short-interest fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "short_interest": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Retail Sentiment ───────────────────────────────────────────────────

@router.get("/retail-sentiment/{ticker}")
async def get_retail_sentiment(ticker: str):
    cache = get_cache_manager()
    cache_key = f"retail_sentiment:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.retail_sentiment import retail_sentiment_service
            data = await retail_sentiment_service.get_sentiment(ticker)
            score = retail_sentiment_service.score_sentiment(data)
            return {"status": "live", "ticker": ticker.upper(), "sentiment": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("retail-sentiment fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "sentiment": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Technical Analysis ──────────────────────────────────────────────────

@router.get("/technical-analysis/{ticker}")
async def get_technical_analysis(ticker: str):
    cache = get_cache_manager()
    cache_key = f"technical_analysis:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.technical_analysis import technical_analysis_service
            data = await technical_analysis_service.get_indicators(ticker)
            score = technical_analysis_service.score_technical(data)
            return {"status": "live", "ticker": ticker.upper(), "indicators": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("technical-analysis fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "indicators": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Financial Fundamentals ──────────────────────────────────────────────

@router.get("/fundamentals/{ticker}")
async def get_fundamentals(ticker: str):
    cache = get_cache_manager()
    cache_key = f"fundamentals:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.financial_fundamentals import financial_fundamentals_service
            data = await financial_fundamentals_service.get_fundamentals(ticker)
            score = financial_fundamentals_service.score_fundamentals(data)
            return {"status": "live", "ticker": ticker.upper(), "fundamentals": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("fundamentals fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "fundamentals": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Alpha Score (Aggregated) ─────────────────────────────────────────────

@router.get("/alpha-score/{ticker}")
async def get_alpha_score(ticker: str):
    cache = get_cache_manager()
    cache_key = f"alpha_score:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.intelligence.alpha_aggregator import alpha_aggregator
            data = await alpha_aggregator.get_alpha_score(ticker)
            data["status"] = "live"
            data["timestamp"] = _now()
            return data
        except Exception as e:
            logger.warning("alpha-score fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "alpha_score": 0, "signal": "NEUTRAL", "components": {}, "timestamp": _now()}
    return data


# ── OSINT: Institutional Holdings ─────────────────────────────────────────────

@router.get("/institutional-holdings/{ticker}")
async def get_institutional_holdings(ticker: str):
    cache = get_cache_manager()
    cache_key = f"institutional_holdings:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.institutional_holdings import institutional_holdings_service
            data = await institutional_holdings_service.get_holdings(ticker)
            score = institutional_holdings_service.score_institutional_activity(data)
            return {"status": "live", "ticker": ticker.upper(), "holdings": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("institutional-holdings fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "holdings": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Options Flow ───────────────────────────────────────────────────────

@router.get("/options-flow/{ticker}")
async def get_options_flow(ticker: str):
    cache = get_cache_manager()
    cache_key = f"options_flow:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.options_flow import options_flow_service
            data = await options_flow_service.get_options_flow(ticker)
            score = options_flow_service.score_options_flow(data)
            return {"status": "live", "ticker": ticker.upper(), "options_flow": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("options-flow fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "options_flow": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Twitter Sentiment ───────────────────────────────────────────────────

@router.get("/twitter-sentiment/{ticker}")
async def get_twitter_sentiment(ticker: str):
    cache = get_cache_manager()
    cache_key = f"twitter_sentiment:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.twitter_sentiment import twitter_sentiment_service
            data = await twitter_sentiment_service.get_sentiment(ticker)
            score = twitter_sentiment_service.score_twitter_sentiment(data)
            return {"status": "live", "ticker": ticker.upper(), "sentiment": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("twitter-sentiment fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "sentiment": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Earnings Transcripts ────────────────────────────────────────────────

@router.get("/earnings-transcripts/{ticker}")
async def get_earnings_transcripts(ticker: str):
    cache = get_cache_manager()
    cache_key = f"earnings_transcripts:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.earnings_transcripts import earnings_transcripts_service
            data = await earnings_transcripts_service.get_transcripts(ticker)
            score = earnings_transcripts_service.score_earnings_sentiment(data)
            return {"status": "live", "ticker": ticker.upper(), "transcripts": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("earnings-transcripts fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "transcripts": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: FDA Trials ──────────────────────────────────────────────────────────

@router.get("/fda-trials/{company}")
async def get_fda_trials(company: str):
    cache = get_cache_manager()
    cache_key = f"fda_trials:{company}"

    async def fetch():
        try:
            from app.services.data.fda_trials import fda_trials_service
            data = await fda_trials_service.get_trials(company)
            score = fda_trials_service.score_fda_pipeline(data)
            return {"status": "live", "company": company, "trials": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("fda-trials fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "company": company, "trials": {}, "score": 0, "timestamp": _now()}
    return data


# ── OSINT: Patents ─────────────────────────────────────────────────────────────

@router.get("/patents/{company}")
async def get_patents(company: str):
    cache = get_cache_manager()
    cache_key = f"patents:{company}"

    async def fetch():
        try:
            from app.services.data.patents import patents_service
            data = await patents_service.get_patents(company)
            score = patents_service.score_patent_activity(data)
            return {"status": "live", "company": company, "patents": data, "score": round(score, 2), "timestamp": _now()}
        except Exception as e:
            logger.warning("patents fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "company": company, "patents": {}, "score": 0, "timestamp": _now()}
    return data


# ── ML: Beneish M-Score ────────────────────────────────────────────────────────

@router.get("/m-score/{ticker}")
async def get_m_score(ticker: str):
    cache = get_cache_manager()
    cache_key = f"m_score:{ticker.upper()}"

    async def fetch():
        try:
            from app.ml.m_score import beneish_m_score
            data = await beneish_m_score.calculate(ticker)
            data["status"] = "live"
            return data
        except Exception as e:
            logger.warning("m-score fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "m_score": None, "manipulation_likelihood": "unknown", "timestamp": _now()}
    return data


# ── ML: Altman Z-Score ─────────────────────────────────────────────────────────

@router.get("/z-score/{ticker}")
async def get_z_score(ticker: str):
    cache = get_cache_manager()
    cache_key = f"z_score:{ticker.upper()}"

    async def fetch():
        try:
            from app.ml.z_score import altman_z_score
            data = await altman_z_score.calculate(ticker)
            data["status"] = "live"
            return data
        except Exception as e:
            logger.warning("z-score fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "z_score": None, "zone": "unknown", "timestamp": _now()}
    return data


# ── Trading: Factor Rotation ────────────────────────────────────────────────────

@router.get("/factor-rotation")
async def get_factor_rotation(regime: str = None):
    cache = get_cache_manager()
    cache_key = f"factor_rotation:{regime or 'auto'}"

    async def fetch():
        try:
            from app.services.intelligence.factor_rotation import factor_rotation_service
            data = await factor_rotation_service.get_rotation(regime)
            data["status"] = "live"
            return data
        except Exception as e:
            logger.warning("factor-rotation fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "regime": "sideways", "timestamp": _now()}
    return data


# ── Trading: Technical Patterns ─────────────────────────────────────────────────

@router.get("/technical-patterns/{ticker}")
async def get_technical_patterns(ticker: str):
    cache = get_cache_manager()
    cache_key = f"technical_patterns:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.trading.pattern_detection import pattern_detection_service
            data = await pattern_detection_service.detect_patterns(ticker)
            data["status"] = "live"
            return data
        except Exception as e:
            logger.warning("technical-patterns fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "patterns": [], "signal": "neutral", "timestamp": _now()}
    return data


# ── Trading: Portfolio Optimize ─────────────────────────────────────────────────

@router.post("/portfolio/optimize")
async def post_portfolio_optimize(holdings: list):
    try:
        from app.services.trading.portfolio_optimizer import portfolio_optimizer
        data = await portfolio_optimizer.optimize(holdings)
        data["status"] = "live"
        return data
    except Exception as e:
        logger.warning("portfolio optimize failed: %s", e)
        return {"status": "error", "error": str(e), "timestamp": _now()}


# ── Trading: Risk Metrics ───────────────────────────────────────────────────────

@router.post("/portfolio/risk-metrics")
async def post_risk_metrics(tickers: list):
    try:
        from app.services.trading.portfolio_optimizer import portfolio_optimizer
        data = await portfolio_optimizer.calculate_risk_metrics(tickers)
        data["status"] = "live"
        return data
    except Exception as e:
        logger.warning("risk metrics failed: %s", e)
        return {"status": "error", "error": str(e), "timestamp": _now()}


# ── Trading: Backtest ───────────────────────────────────────────────────────────

@router.get("/backtest/{ticker}")
async def get_backtest(ticker: str, strategy: str = "alpha_momentum",
                       start_date: str = None, end_date: str = None,
                       initial_capital: float = 10000):
    cache = get_cache_manager()
    cache_key = f"backtest:{ticker.upper()}:{strategy}"

    async def fetch():
        try:
            from app.services.trading.backtester import backtester
            data = await backtester.run(ticker, strategy, start_date, end_date, initial_capital)
            data["status"] = "live"
            return data
        except Exception as e:
            logger.warning("backtest fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "strategy": strategy, "total_return_pct": 0, "timestamp": _now()}
    return data


# ── Corporate Actions ───────────────────────────────────────────────────────────

@router.get("/corporate-actions/{ticker}")
async def get_corporate_actions(ticker: str):
    cache = get_cache_manager()
    cache_key = f"corporate_actions:{ticker.upper()}"

    async def fetch():
        try:
            from app.services.data.corporate_actions import corporate_actions_service
            data = await corporate_actions_service.get_actions(ticker)
            data["status"] = "live"
            return data
        except Exception as e:
            logger.warning("corporate-actions fetch failed: %s", e)
            return None

    result = await cache.get_or_fetch(cache_key, fetch, data_type="osint")
    data = result.data if result and result.data else {"status": "bootstrap", "ticker": ticker.upper(), "dividends": [], "splits": [], "timestamp": _now()}
    return data


# ── Reports: Generate Dossier ───────────────────────────────────────────────────

@router.post("/reports/generate-dossier")
async def post_generate_dossier(ticker: str):
    try:
        from app.services.infrastructure.report_generator import report_generator
        data = await report_generator.generate_dossier(ticker)
        data["status"] = "live"
        return data
    except Exception as e:
        logger.warning("dossier generation failed: %s", e)
        return {"status": "error", "error": str(e), "timestamp": _now()}


# ── Alerts: Telegram Test ───────────────────────────────────────────────────────

@router.post("/alerts/telegram-test")
async def post_telegram_test(ticker: str = "AAPL", signal: str = "NEUTRAL", score: float = 0):
    try:
        from app.services.infrastructure.telegram_bot import telegram_bot
        sent = await telegram_bot.send_alert(ticker, signal, score, ["Test alert from MarketPulse"])
        return {"status": "live", "sent": sent, "enabled": telegram_bot.enabled, "timestamp": _now()}
    except Exception as e:
        logger.warning("telegram test failed: %s", e)
        return {"status": "error", "error": str(e), "timestamp": _now()}
