"""
Isolation Forest Anomaly Detector — Detects unusual price/volume patterns
that may indicate market manipulation, news-driven events, or regime changes.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from app.core.disclaimer import DISCLAIMER

logger = logging.getLogger(__name__)



class IsolationForestDetector:
    """Isolation Forest for detecting anomalous price/volume behavior.

    Features:
    - Returns (1d, 5d)
    - Volume ratio (current / 20d avg)
    - RSI
    - MACD histogram
    - Bollinger %B
    - Intraday range
    """

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self._model = None
        self._scaler = None

    def fit(self, ticker: str, period: str = "1y") -> Dict:
        """Fit the model on historical data for a ticker."""
        try:
            import yfinance as yf
            from sklearn.ensemble import IsolationForest
            from sklearn.preprocessing import StandardScaler
        except ImportError as e:
            logger.warning("Dependencies not available: %s", e)
            return {"status": "error", "error": str(e)}

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty or len(hist) < 60:
                return {"status": "error", "error": "Insufficient data"}

            features = self._extract_features(hist)
            if features is None or len(features) < 30:
                return {"status": "error", "error": "Insufficient feature data"}

            self._scaler = StandardScaler()
            X = self._scaler.fit_transform(features)

            self._model = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=42,
                n_jobs=-1,
            )
            self._model.fit(X)

            scores = self._model.decision_function(X)
            predictions = self._model.predict(X)

            n_anomalies = int((predictions == -1).sum())

            return {
                "status": "success",
                "ticker": ticker,
                "n_samples": len(features),
                "n_anomalies": n_anomalies,
                "anomaly_rate": round(n_anomalies / len(features) * 100, 2),
                "mean_anomaly_score": round(float(scores.mean()), 4),
                "disclaimer": DISCLAIMER,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.warning("Isolation Forest fit failed for %s: %s", ticker, e)
            return {"status": "error", "error": str(e)}

    def detect(self, ticker: str, period: str = "6mo") -> Dict:
        """Detect anomalies in recent data."""
        try:
            import yfinance as yf
        except ImportError:
            return {"status": "error", "error": "yfinance not available"}

        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty or len(hist) < 30:
                return {"status": "error", "error": "Insufficient data"}

            features = self._extract_features(hist)
            if features is None or len(features) < 10:
                return {"status": "error", "error": "Insufficient feature data"}

            if self._model is not None and self._scaler is not None:
                X = self._scaler.transform(features)
                scores = self._model.decision_function(X)
                predictions = self._model.predict(X)

                recent_scores = scores[-5:] if len(scores) >= 5 else scores
                recent_preds = predictions[-5:] if len(predictions) >= 5 else predictions

                is_anomaly = bool((recent_preds == -1).any())
                avg_score = float(recent_scores.mean())

                anomaly_days = []
                for i in range(len(predictions)):
                    if predictions[i] == -1 and i < len(hist):
                        anomaly_days.append(str(hist.index[i].date()))

                return {
                    "status": "live",
                    "ticker": ticker,
                    "is_anomaly": is_anomaly,
                    "anomaly_score": round(avg_score, 4),
                    "recent_predictions": [int(p) for p in recent_preds],
                    "anomaly_days": anomaly_days[-10:],
                    "n_anomalies_total": int((predictions == -1).sum()),
                    "disclaimer": DISCLAIMER,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                returns = hist["Close"].pct_change().dropna()
                volume_ratio = hist["Volume"] / hist["Volume"].rolling(20).mean()
                rsi = self._calc_rsi(hist["Close"])

                z_scores = np.abs((returns - returns.mean()) / (returns.std() + 1e-8))
                vol_z = np.abs((volume_ratio - volume_ratio.mean()) / (volume_ratio.std() + 1e-8))

                recent_z = z_scores.iloc[-5:] if len(z_scores) >= 5 else z_scores
                recent_vol_z = vol_z.iloc[-5:] if len(vol_z) >= 5 else vol_z

                is_anomaly = bool((recent_z > 2.5).any() or (recent_vol_z > 2.5).any())

                return {
                    "status": "live",
                    "ticker": ticker,
                    "is_anomaly": is_anomaly,
                    "anomaly_score": round(float(recent_z.mean()), 4),
                    "note": "Rule-based detection (model not fitted)",
                    "disclaimer": DISCLAIMER,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.warning("Anomaly detection failed for %s: %s", ticker, e)
            return {"status": "error", "error": str(e)}

    def _extract_features(self, hist: pd.DataFrame) -> Optional[np.ndarray]:
        try:
            close = hist["Close"]
            volume = hist["Volume"]
            high = hist["High"]
            low = hist["Low"]

            returns_1d = close.pct_change()
            returns_5d = close.pct_change(5)
            volume_ratio = volume / volume.rolling(20).mean()
            rsi = self._calc_rsi_series(close)
            macd_hist = self._calc_macd_histogram(close)
            bb_pctb = self._calc_bollinger_pctb(close)
            intraday_range = (high - low) / close

            features = pd.DataFrame({
                "returns_1d": returns_1d,
                "returns_5d": returns_5d,
                "volume_ratio": volume_ratio,
                "rsi": rsi,
                "macd_hist": macd_hist,
                "bb_pctb": bb_pctb,
                "intraday_range": intraday_range,
            })

            features = features.dropna()
            if len(features) < 10:
                return None

            return features.values

        except Exception as e:
            logger.debug("Feature extraction failed: %s", e)
            return None

    def _calc_rsi(self, prices, period: int = 14):
        if len(prices) < period + 1:
            return 50.0
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    def _calc_rsi_series(self, prices, period: int = 14):
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calc_macd_histogram(self, prices):
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        return macd - signal

    def _calc_bollinger_pctb(self, prices, period: int = 20):
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        return (prices - lower) / (upper - lower + 1e-8)


anomaly_detector = IsolationForestDetector()
