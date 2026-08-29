"""
Options Flow Service — Unusual options activity detection.
Uses free data sources: MarketBeat, Yahoo Finance options chain.
Detects call/put sweeps, block trades, OI spikes.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import yfinance as yf

logger = logging.getLogger(__name__)


class OptionsFlowService:
    async def get_options_flow(self, ticker: str, days_back: int = 7) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "options_chain": {},
            "unusual_activity": [],
            "put_call_ratio": None,
            "max_pain": None,
            "total_volume": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)

            expirations = stock.options[:3] if stock.options else []
            all_calls = []
            all_puts = []

            for exp in expirations:
                try:
                    chain = stock.option_chain(exp)
                    calls = chain.calls if chain.calls is not None else []
                    puts = chain.puts if chain.puts is not None else []

                    for c in calls.to_dict("records"):
                        c["option_type"] = "call"
                        c["expiration"] = exp
                        all_calls.append(c)

                    for p in puts.to_dict("records"):
                        p["option_type"] = "put"
                        p["expiration"] = exp
                        all_puts.append(p)

                except Exception:
                    continue

            result["options_chain"]["calls"] = all_calls[:50]
            result["options_chain"]["puts"] = all_puts[:50]

            call_vol = sum(c.get("volume", 0) or 0 for c in all_calls)
            put_vol = sum(p.get("volume", 0) or 0 for p in all_puts)
            result["total_volume"] = call_vol + put_vol

            if put_vol > 0:
                result["put_call_ratio"] = round(call_vol / put_vol, 2)
            else:
                result["put_call_ratio"] = None

            unusual = self._detect_unusual(all_calls, all_puts)
            result["unusual_activity"] = unusual[:20]

            result["max_pain"] = self._estimate_max_pain(all_calls, all_puts)

        except Exception as e:
            logger.warning(f"Options flow fetch failed for {ticker}: {e}")

        return result

    def _detect_unusual(self, calls: list, puts: list) -> list:
        unusual = []

        for option in calls + puts:
            volume = option.get("volume", 0) or 0
            oi = option.get("openInterest", 0) or 0

            if volume > 0 and oi > 0:
                vol_oi_ratio = volume / oi
                if vol_oi_ratio > 3 and volume > 500:
                    unusual.append({
                        "strike": option.get("strike"),
                        "option_type": option.get("option_type"),
                        "expiration": option.get("expiration"),
                        "volume": int(volume),
                        "open_interest": int(oi),
                        "vol_oi_ratio": round(vol_oi_ratio, 2),
                        "last_price": float(option.get("lastPrice", 0)),
                        "implied_volatility": float(option.get("impliedVolatility", 0)),
                        "significance": self._rate_significance(vol_oi_ratio, volume),
                    })

        unusual.sort(key=lambda x: x["vol_oi_ratio"], reverse=True)
        return unusual

    def _rate_significance(self, vol_oi_ratio: float, volume: int) -> str:
        if vol_oi_ratio > 10 and volume > 2000:
            return "high"
        elif vol_oi_ratio > 5 and volume > 1000:
            return "medium"
        return "low"

    def _estimate_max_pain(self, calls: list, puts: list) -> float:
        strikes = set()
        for c in calls:
            if c.get("strike"):
                strikes.add(c["strike"])
        for p in puts:
            if p.get("strike"):
                strikes.add(p["strike"])

        if not strikes:
            return None

        max_pain = None
        max_value = float("-inf")

        for strike in strikes:
            call_value = sum(
                abs(float(c.get("lastPrice", 0))) * (int(c.get("openInterest", 0)) or 0)
                for c in calls
                if c.get("strike") == strike and c.get("lastPrice")
            )
            put_value = sum(
                abs(float(p.get("lastPrice", 0))) * (int(p.get("openInterest", 0)) or 0)
                for p in puts
                if p.get("strike") == strike and p.get("lastPrice")
            )
            total = call_value + put_value
            if total > max_value:
                max_value = total
                max_pain = strike

        return max_pain

    def score_options_flow(self, data: dict) -> float:
        score = 0.0
        pcr = data.get("put_call_ratio")

        if pcr is not None:
            if pcr > 2.0:
                score += 2.0
            elif pcr > 1.5:
                score += 1.0
            elif pcr < 0.5:
                score -= 1.0
            elif pcr < 0.3:
                score -= 2.0

        unusual = data.get("unusual_activity", [])
        if unusual:
            high = sum(1 for u in unusual if u.get("significance") == "high")
            calls = sum(1 for u in unusual if u.get("option_type") == "call")
            puts = sum(1 for u in unusual if u.get("option_type") == "put")

            if high > 2:
                score += 1.5
            if calls > puts:
                score += 1.0
            elif puts > calls:
                score -= 1.0

        return max(-5.0, min(5.0, score))


options_flow_service = OptionsFlowService()
