"""
Alpaca Market Data Service
Replaces yfinance for real-time stock prices.
REST snapshots are used for on-demand calls; WebSocket pushes to an in-memory cache.
Falls back gracefully when ALPACA_API_KEY / ALPACA_SECRET_KEY are not configured.
"""
import os
import logging
import threading
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── In-memory price cache (shared by REST + WebSocket paths) ──────────────────
_price_cache: Dict[str, dict] = {}
_cache_lock  = threading.Lock()
_ws_thread   = None


def _build_price_entry(ticker: str, price: float, prev_close: float, volume: int = 0, source: str = "alpaca") -> dict:
    change     = price - prev_close if prev_close else 0.0
    change_pct = (change / prev_close * 100) if prev_close else 0.0
    return {
        "ticker":         ticker,
        "current_price":  round(price, 2),
        "previous_close": round(prev_close, 2),
        "change":         round(change, 2),
        "change_percent": round(change_pct, 4),
        "volume":         volume,
        "is_valid":       price > 0,
        "source":         source,
        "timestamp":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


class AlpacaService:
    """
    Wraps Alpaca Market Data API v2.
    Free tier (IEX feed) gives real-time quotes with ~15-min delay for non-subscribers;
    SIP feed requires a paid subscription but the same code works for both.
    """

    SNAPSHOT_URL = "https://data.alpaca.markets/v2/stocks/snapshots"
    WS_URL       = "wss://stream.data.alpaca.markets/v2/iex"

    def __init__(self):
        self.api_key    = os.getenv("ALPACA_API_KEY", "")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY", "")
        self._available = bool(self.api_key and self.secret_key)
        if not self._available:
            logger.warning("Alpaca keys not configured (ALPACA_API_KEY / ALPACA_SECRET_KEY). "
                           "Stock prices will fall back to yfinance.")

    @property
    def available(self) -> bool:
        return self._available

    # ── REST snapshots ────────────────────────────────────────────────────────

    def get_snapshots(self, tickers: List[str]) -> Dict[str, dict]:
        """Fetch latest trade / quote / daily bar for each ticker in one REST call."""
        if not self._available or not tickers:
            return {}
        try:
            import requests
            headers = {
                "APCA-API-KEY-ID":     self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key,
            }
            resp = requests.get(
                self.SNAPSHOT_URL,
                params={"symbols": ",".join(tickers), "feed": "iex"},
                headers=headers,
                timeout=8,
            )
            resp.raise_for_status()
            raw = resp.json()

            result: Dict[str, dict] = {}
            for ticker, snap in raw.items():
                latest_trade   = snap.get("latestTrade", {})
                daily_bar      = snap.get("dailyBar",    {})
                prev_daily_bar = snap.get("prevDailyBar",{})

                price      = latest_trade.get("p", 0) or daily_bar.get("c", 0)
                prev_close = prev_daily_bar.get("c", 0)
                volume     = int(daily_bar.get("v", 0))

                entry = _build_price_entry(ticker, price, prev_close, volume)
                result[ticker]               = entry
                with _cache_lock:
                    _price_cache[ticker] = entry

            logger.info("Alpaca snapshots fetched for %d tickers", len(result))
            return result

        except Exception as exc:
            logger.error("Alpaca REST snapshot error: %s", exc)
            return {}

    def get_cached(self, tickers: List[str]) -> Dict[str, dict]:
        """Return whatever is in the in-memory cache for these tickers."""
        with _cache_lock:
            return {t: _price_cache[t] for t in tickers if t in _price_cache}

    # ── WebSocket streaming ───────────────────────────────────────────────────

    def start_stream(self, tickers: List[str]):
        """
        Start a background WebSocket thread that keeps _price_cache warm.
        Call once at startup with the tickers you care about most.
        """
        if not self._available:
            return
        global _ws_thread
        if _ws_thread and _ws_thread.is_alive():
            return  # already running

        def _run():
            try:
                import websocket, json as _json

                def on_open(ws):
                    ws.send(_json.dumps({"action": "auth", "key": self.api_key, "secret": self.secret_key}))

                def on_message(ws, message):
                    msgs = _json.loads(message)
                    for m in msgs:
                        if m.get("T") == "q":   # quote
                            t  = m.get("S", "")
                            bp = m.get("bp", 0)  # bid price
                            ap = m.get("ap", 0)  # ask price
                            mid = (bp + ap) / 2 if bp and ap else bp or ap
                            if t and mid:
                                with _cache_lock:
                                    prev = _price_cache.get(t, {}).get("current_price", mid)
                                    _price_cache[t] = _build_price_entry(t, mid, prev, 0, "alpaca-ws")
                        elif m.get("T") == "authenticated":
                            ws.send(_json.dumps({"action": "subscribe", "quotes": tickers}))

                def on_error(ws, err):
                    logger.error("Alpaca WS error: %s", err)

                ws_app = websocket.WebSocketApp(
                    self.WS_URL,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                )
                ws_app.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                logger.error("Alpaca WS thread crashed: %s", exc)

        _ws_thread = threading.Thread(target=_run, daemon=True, name="alpaca-ws")
        _ws_thread.start()
        logger.info("Alpaca WebSocket stream started for %d tickers", len(tickers))


# ── Module-level singleton ────────────────────────────────────────────────────
alpaca_service = AlpacaService()
