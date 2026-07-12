"""
Factor Rotation Service — Maps market regime to factor exposure.
Bull → Momentum/Growth, Bear → Defensive/Low Vol, Sideways → Value, Volatile → Cash/Hedge.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)

REGIME_FACTOR_MAP = {
    "bull": {
        "primary": "momentum",
        "secondary": "growth",
        "avoid": "defensive",
        "allocation": {"momentum": 0.40, "growth": 0.30, "value": 0.15, "defensive": 0.10, "cash": 0.05},
    },
    "bear": {
        "primary": "defensive",
        "secondary": "low_vol",
        "avoid": "growth",
        "allocation": {"defensive": 0.40, "low_vol": 0.25, "value": 0.15, "cash": 0.15, "momentum": 0.05},
    },
    "sideways": {
        "primary": "value",
        "secondary": "quality",
        "avoid": "momentum",
        "allocation": {"value": 0.35, "quality": 0.25, "defensive": 0.15, "momentum": 0.10, "cash": 0.15},
    },
    "volatile": {
        "primary": "cash",
        "secondary": "defensive",
        "avoid": "growth",
        "allocation": {"cash": 0.40, "defensive": 0.25, "low_vol": 0.20, "value": 0.10, "momentum": 0.05},
    },
}

ETF_MAP = {
    "momentum": "MTUM",
    "growth": "VUG",
    "value": "VTV",
    "defensive": "VDC",
    "low_vol": "USMV",
    "quality": "QUAL",
    "cash": "SHY",
}

class FactorRotationService:
    async def get_rotation(self, regime: str = None) -> dict:
        if not regime:
            try:
                from app.ml.regime_detector import regime_detector
                detected = regime_detector.detect()
                regime = detected.get("regime", "sideways")
            except Exception:
                regime = "sideways"

        regime = regime.lower()
        if regime not in REGIME_FACTOR_MAP:
            regime = "sideways"

        config = REGIME_FACTOR_MAP[regime]

        etf_prices = {}
        for factor, ticker in ETF_MAP.items():
            try:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="5d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    change = float(hist["Close"].pct_change().iloc[-1] * 100) if len(hist) > 1 else 0
                    etf_prices[factor] = {"ticker": ticker, "price": round(price, 2), "change_pct": round(change, 2)}
            except Exception:
                continue

        return {
            "regime": regime,
            "primary_factor": config["primary"],
            "secondary_factor": config["secondary"],
            "avoid_factor": config["avoid"],
            "recommended_allocation": config["allocation"],
            "etf_prices": etf_prices,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def score_factor_alignment(self, ticker: str, regime: str = None) -> float:
        if not regime:
            regime = "sideways"

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            beta = info.get("beta", 1.0) or 1.0
            pe = info.get("trailingPE", 20) or 20
            sector = info.get("sector", "")

            if regime == "bull":
                if beta > 1.2:
                    return 2.0
                elif beta > 0.9:
                    return 0.5
                else:
                    return -1.0

            elif regime == "bear":
                if beta < 0.8:
                    return 2.0
                elif sector in ("Utilities", "Consumer Defensive", "Healthcare"):
                    return 1.0
                else:
                    return -1.0

            elif regime == "sideways":
                if pe < 15 and pe > 0:
                    return 2.0
                elif pe < 20:
                    return 1.0
                else:
                    return -0.5

            elif regime == "volatile":
                if beta < 0.7:
                    return 2.0
                elif sector in ("Utilities", "Healthcare"):
                    return 1.0
                else:
                    return -1.5

        except Exception:
            pass

        return 0.0


factor_rotation_service = FactorRotationService()
