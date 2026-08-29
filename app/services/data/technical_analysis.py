"""
Technical Analysis Service — RSI, MACD, Bollinger Bands, Moving Averages.
All computed from yfinance OHLCV data. No API keys needed.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class TechnicalAnalysisService:
    async def get_indicators(self, ticker: str, period: str = "6mo") -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "price": None,
            "rsi": None,
            "macd": None,
            "macd_signal": None,
            "macd_histogram": None,
            "bollinger_upper": None,
            "bollinger_middle": None,
            "bollinger_lower": None,
            "sma_20": None,
            "sma_50": None,
            "sma_200": None,
            "volume_avg_20": None,
            "volume_current": None,
            "signals": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)

            if hist.empty:
                return result

            close = hist["Close"]
            volume = hist["Volume"]
            high = hist["High"]
            low = hist["Low"]

            result["price"] = round(float(close.iloc[-1]), 2)

            result["rsi"] = self._calc_rsi(close)
            result["macd"], result["macd_signal"], result["macd_histogram"] = self._calc_macd(close)
            bb_upper, bb_mid, bb_lower = self._calc_bollinger(close)
            result["bollinger_upper"] = round(bb_upper, 2) if bb_upper else None
            result["bollinger_middle"] = round(bb_mid, 2) if bb_mid else None
            result["bollinger_lower"] = round(bb_lower, 2) if bb_lower else None
            result["sma_20"] = round(float(close.rolling(20).mean().iloc[-1]), 2) if len(close) >= 20 else None
            result["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2) if len(close) >= 50 else None
            result["sma_200"] = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None
            result["volume_avg_20"] = round(float(volume.rolling(20).mean().iloc[-1]), 0) if len(volume) >= 20 else None
            result["volume_current"] = round(float(volume.iloc[-1]), 0)
            result["signals"] = self._generate_signals(close, volume, high, low, result)

        except Exception as e:
            logger.warning(f"Technical analysis failed for {ticker}: {e}")

        return result

    def _calc_rsi(self, prices, period: int = 14):
        if len(prices) < period + 1:
            return None
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi.iloc[-1]), 2)

    def _calc_macd(self, prices):
        if len(prices) < 26:
            return None, None, None
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        return (
            round(float(macd.iloc[-1]), 4),
            round(float(signal.iloc[-1]), 4),
            round(float(histogram.iloc[-1]), 4),
        )

    def _calc_bollinger(self, prices, period: int = 20):
        if len(prices) < period:
            return None, None, None
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return float(upper.iloc[-1]), float(sma.iloc[-1]), float(lower.iloc[-1])

    def _generate_signals(self, close, volume, high, low, indicators: dict) -> list:
        signals = []
        rsi = indicators.get("rsi")
        price = indicators.get("price")

        if rsi is not None:
            if rsi > 70:
                signals.append("RSI_OVERBOUGHT")
            elif rsi < 30:
                signals.append("RSI_OVERSOLD")
            elif rsi > 60:
                signals.append("RSI_BULLISH")
            elif rsi < 40:
                signals.append("RSI_BEARISH")

        macd_hist = indicators.get("macd_histogram")
        if macd_hist is not None:
            if macd_hist > 0:
                signals.append("MACD_BULLISH")
            else:
                signals.append("MACD_BEARISH")

        sma_20 = indicators.get("sma_20")
        sma_50 = indicators.get("sma_50")
        if sma_20 and sma_50 and price:
            if sma_20 > sma_50:
                signals.append("SMA_GOLDEN_CROSS")
            else:
                signals.append("SMA_DEATH_CROSS")

        bb_upper = indicators.get("bollinger_upper")
        bb_lower = indicators.get("bollinger_lower")
        if bb_upper and bb_lower and price:
            if price >= bb_upper:
                signals.append("BOLLINGER_TOUCH_UPPER")
            elif price <= bb_lower:
                signals.append("BOLLINGER_TOUCH_LOWER")

        volume_avg = indicators.get("volume_avg_20")
        volume_curr = indicators.get("volume_current")
        if volume_avg and volume_curr:
            if volume_curr > volume_avg * 2:
                signals.append("VOLUME_SPIKE")
            elif volume_curr > volume_avg * 1.5:
                signals.append("VOLUME_HIGH")

        return signals

    def score_technical(self, indicators: dict) -> float:
        """Score technical analysis from -5 (bearish) to +5 (bullish)."""
        score = 0.0
        signals = indicators.get("signals", [])

        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < 30:
                score += 2.0
            elif rsi < 40:
                score += 1.0
            elif rsi > 70:
                score -= 2.0
            elif rsi > 60:
                score -= 1.0

        for s in signals:
            if s in ("MACD_BULLISH", "SMA_GOLDEN_CROSS"):
                score += 1.5
            elif s in ("MACD_BEARISH", "SMA_DEATH_CROSS"):
                score -= 1.5
            if s == "VOLUME_SPIKE":
                score -= 0.5

        if "BOLLINGER_TOUCH_LOWER" in signals:
            score += 1.0
        elif "BOLLINGER_TOUCH_UPPER" in signals:
            score -= 1.0

        return max(-5.0, min(5.0, score))


technical_analysis_service = TechnicalAnalysisService()
