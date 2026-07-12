"""
Background Scheduler — news, market, macro, regime, risk retraining, alerts.
"""
import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        self.thread = None

    def add_task(self, name: str, func: Callable, interval_seconds: int):
        self.tasks.append({"name": name, "func": func, "interval": interval_seconds, "last_run": 0})
        logger.info("Scheduled task '%s' every %ds", name, interval_seconds)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Background scheduler started (%d tasks)", len(self.tasks))

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _run_loop(self):
        while self.running:
            now = time.time()
            for task in self.tasks:
                if now - task["last_run"] >= task["interval"]:
                    try:
                        task["func"]()
                        task["last_run"] = now
                    except Exception as e:
                        logger.error("Task '%s' failed: %s", task["name"], e)
            time.sleep(10)


scheduler = BackgroundScheduler()


def start_background_tasks():
    def news_refresh():
        try:
            from app.services.news_aggregator import news_aggregator_layer
            from app.config import TRACKED_COMPANIES
            tickers = [t for t in TRACKED_COMPANIES if isinstance(t, str) and t]
            articles = news_aggregator_layer.ingest_all(tickers or ["AAPL"])
            logger.info("news_refresh: %d articles for %d tickers", len(articles), len(tickers))
        except Exception as e:
            logger.error("news_refresh failed: %s", e)

    def market_refresh():
        try:
            import yfinance as yf
            from app.config import COMPANY_TICKERS
            tickers = list(COMPANY_TICKERS.values())[:5]
            if tickers:
                yf.download(tickers, period="1d", interval="1m", progress=False, threads=False)
                logger.info("market_refresh: done")
        except Exception as e:
            logger.error("market_refresh failed: %s", e)

    def macro_refresh():
        logger.info("macro_refresh: FRED + commodities refresh (see macro_economic.py)")

    def regime_detection():
        try:
            from app.ml.regime_detector import regime_detector
            r = regime_detector.detect()
            logger.info("regime_detection: %s (conf=%.2f)", r.get("regime"), r.get("confidence"))
        except Exception as e:
            logger.error("regime_detection failed: %s", e)

    def risk_scorer_retrain():
        try:
            from app.ml.risk_scorer import risk_scorer
            risk_scorer.retrain()
            logger.info("risk_scorer_retrain: complete")
        except Exception as e:
            logger.error("risk_scorer_retrain failed: %s", e)

    _last_alerted: dict = {}

    def alert_generation():
        try:
            import asyncio
            from app.services.infrastructure.telegram_bot import telegram_bot
            if not telegram_bot.enabled:
                logger.debug("alert_generation: telegram not configured, skipping")
                return

            from app.config import COMPANY_TICKERS
            from app.services.intelligence.alpha_aggregator import alpha_aggregator

            async def scan():
                for ticker in list(COMPANY_TICKERS.values())[:5]:
                    result = await alpha_aggregator.get_alpha_score(ticker)
                    signal = result.get("signal", "NEUTRAL")
                    if signal in ("STRONG_BUY", "STRONG_SELL") and _last_alerted.get(ticker) != signal:
                        sent = await telegram_bot.send_alert(
                            ticker, signal, result.get("alpha_score", 0.0),
                            reasons=result.get("active_signals", []),
                        )
                        if sent:
                            _last_alerted[ticker] = signal

            asyncio.run(scan())
            logger.info("alert_generation: scan complete")
        except Exception as e:
            logger.error("alert_generation failed: %s", e)

    scheduler.add_task("news_refresh",        news_refresh,        300)
    scheduler.add_task("market_refresh",       market_refresh,      60)
    scheduler.add_task("macro_refresh",        macro_refresh,       3600)
    scheduler.add_task("regime_detection",     regime_detection,    1800)
    scheduler.add_task("risk_scorer_retrain",  risk_scorer_retrain, 86400)
    scheduler.add_task("alert_generation",     alert_generation,    300)
    scheduler.start()
