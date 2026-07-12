"""
Pattern Detection Service — Rule-based chart pattern recognition.
Detects: Head & Shoulders, Double Top/Bottom, Flag/Pennant.
Uses yfinance OHLCV data with pandas-ta indicators.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class PatternDetectionService:
    async def detect_patterns(self, ticker: str, period: str = "6mo") -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "patterns": [],
            "total_patterns": 0,
            "signal": "neutral",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            data = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
            if data.empty or len(data) < 30:
                return result

            close = data["Close"].values
            high = data["High"].values
            low = data["Low"].values
            volume = data["Volume"].values if "Volume" in data.columns else None

            patterns = []

            hs = self._detect_head_shoulders(close)
            if hs:
                patterns.append(hs)

            db = self._detect_double_top_bottom(close)
            if db:
                patterns.append(db)

            flag = self._detect_flag_pennant(close, volume)
            if flag:
                patterns.append(flag)

            bb = self._detect_bullish_bearish_engulfing(close, high, low)
            if bb:
                patterns.append(bb)

            result["patterns"] = patterns
            result["total_patterns"] = len(patterns)

            bullish = sum(1 for p in patterns if p.get("direction") == "bullish")
            bearish = sum(1 for p in patterns if p.get("direction") == "bearish")
            if bullish > bearish:
                result["signal"] = "bullish"
            elif bearish > bullish:
                result["signal"] = "bearish"

        except Exception as e:
            logger.warning(f"Pattern detection failed for {ticker}: {e}")

        return result

    def _detect_head_shoulders(self, close: np.ndarray) -> Optional[dict]:
        if len(close) < 50:
            return None
        try:
            mid = len(close) // 2
            left = close[mid - 15:mid - 5] if mid > 15 else close[:10]
            head = close[mid - 5:mid + 5]
            right = close[mid + 5:mid + 15] if mid + 15 < len(close) else close[-10:]

            left_peak = np.max(left)
            head_peak = np.max(head)
            right_peak = np.max(right)

            if head_peak > left_peak and head_peak > right_peak:
                neckline = (np.min(left[-3:]) + np.min(right[:3])) / 2
                if head_peak - neckline > (head_peak - left_peak) * 0.5:
                    return {
                        "pattern": "head_and_shoulders",
                        "direction": "bearish",
                        "confidence": "medium",
                        "neckline": round(float(neckline), 2),
                        "target": round(float(neckline - (head_peak - neckline)), 2),
                    }
        except Exception:
            pass
        return None

    def _detect_double_top_bottom(self, close: np.ndarray) -> Optional[dict]:
        if len(close) < 40:
            return None
        try:
            segment_len = len(close) // 3
            first = close[:segment_len]
            second = close[segment_len:2 * segment_len]
            third = close[2 * segment_len:]

            first_peak = np.max(first)
            second_peak = np.max(second)
            first_trough = np.min(first)
            second_trough = np.min(second)

            price_level = close[-1]

            if abs(first_peak - second_peak) / first_peak < 0.03:
                if price_level < first_peak * 0.97:
                    return {
                        "pattern": "double_top",
                        "direction": "bearish",
                        "confidence": "medium",
                        "resistance": round(float(first_peak), 2),
                    }

            if abs(first_trough - second_trough) / first_trough < 0.03:
                if price_level > first_trough * 1.03:
                    return {
                        "pattern": "double_bottom",
                        "direction": "bullish",
                        "confidence": "medium",
                        "support": round(float(first_trough), 2),
                    }
        except Exception:
            pass
        return None

    def _detect_flag_pennant(self, close: np.ndarray, volume: np.ndarray) -> Optional[dict]:
        if len(close) < 30 or volume is None:
            return None
        try:
            recent = close[-20:]
            recent_vol = volume[-20:]

            first_half_return = (recent[10] - recent[0]) / recent[0]
            second_half_volatility = np.std(recent[10:]) / np.mean(recent[10:])

            if abs(first_half_return) > 0.05 and second_half_volatility < 0.02:
                if first_half_return > 0:
                    return {
                        "pattern": "bull_flag",
                        "direction": "bullish",
                        "confidence": "low",
                        "pole_return_pct": round(float(first_half_return * 100), 2),
                    }
                else:
                    return {
                        "pattern": "bear_flag",
                        "direction": "bearish",
                        "confidence": "low",
                        "pole_return_pct": round(float(first_half_return * 100), 2),
                    }
        except Exception:
            pass
        return None

    def _detect_bullish_bearish_engulfing(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Optional[dict]:
        if len(close) < 3:
            return None
        try:
            prev_open = close[-3]
            prev_close = close[-2]
            curr_open = close[-2]
            curr_close = close[-1]

            prev_range = abs(prev_close - prev_open)
            curr_range = abs(curr_close - curr_open)

            if curr_range > prev_range * 1.2:
                if curr_close > curr_open and prev_close < prev_open and curr_close > prev_open:
                    return {
                        "pattern": "bullish_engulfing",
                        "direction": "bullish",
                        "confidence": "medium",
                    }
                elif curr_close < curr_open and prev_close > prev_open and curr_close < prev_open:
                    return {
                        "pattern": "bearish_engulfing",
                        "direction": "bearish",
                        "confidence": "medium",
                    }
        except Exception:
            pass
        return None


pattern_detection_service = PatternDetectionService()
