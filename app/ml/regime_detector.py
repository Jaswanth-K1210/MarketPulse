"""
Task 1.7 — HMM market regime detector
States: bull | bear | sideways | volatile
Uses yfinance SPY/VIX data; caches regime 30 min to avoid redundant API calls.
Adds market_regime to agent state so all agents can condition on it.
"""
import logging
import time
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

REGIME_LABELS = {0: "bull", 1: "bear", 2: "sideways", 3: "volatile"}
CACHE_TTL = 1800  # 30 min


class RegimeDetector:
    """
    Fits a 4-state Gaussian HMM on SPY 90-day returns + VIX.
    Falls back to rule-based regime if hmmlearn / yfinance unavailable.
    """

    def __init__(self):
        self._model = None
        self._cache: Dict = {"regime": "sideways", "confidence": 0.5, "ts": 0.0}
        self._load_or_build_model()

    def _load_or_build_model(self):
        try:
            from hmmlearn.hmm import GaussianHMM
            self._hmm_class = GaussianHMM
            logger.info("RegimeDetector: hmmlearn available")
        except ImportError:
            logger.warning("hmmlearn not installed — using rule-based regime fallback")
            self._hmm_class = None

    def _fetch_features(self) -> Optional[np.ndarray]:
        """Fetch 90 days of SPY returns + VIX level as 2-feature matrix."""
        try:
            import yfinance as yf
            spy = yf.download("SPY", period="90d", interval="1d", progress=False, auto_adjust=True)
            vix = yf.download("^VIX", period="90d", interval="1d", progress=False, auto_adjust=True)
            if spy.empty or vix.empty:
                return None
            spy_ret = spy["Close"].pct_change().dropna().values
            vix_vals = vix["Close"].reindex(spy["Close"].index).ffill().dropna().values[1:]
            min_len = min(len(spy_ret), len(vix_vals))
            if min_len < 20:
                return None
            return np.column_stack([spy_ret[-min_len:], vix_vals[-min_len:]])
        except Exception as e:
            logger.warning("RegimeDetector: yfinance fetch failed: %s", e)
            return None

    def _fit_hmm(self, X: np.ndarray) -> Dict:
        try:
            model = self._hmm_class(
                n_components=4,
                covariance_type="diag",
                n_iter=200,
                random_state=42,
            )
            model.fit(X)
            self._model = model
            hidden = model.predict(X)
            current_state = int(hidden[-1])

            # Map states to regimes by mean return
            means = model.means_[:, 0]  # SPY return dimension
            order = np.argsort(means)   # low to high return
            state_map = {
                int(order[0]): "bear",
                int(order[1]): "sideways",
                int(order[2]): "bull",
                int(order[3]): "volatile",  # highest volatility, not necessarily return
            }
            # Re-map volatile: highest VIX mean
            vix_means = model.means_[:, 1]
            volatile_state = int(np.argmax(vix_means))
            if volatile_state in state_map:
                state_map[volatile_state] = "volatile"

            regime = state_map.get(current_state, "sideways")
            probs = model.predict_proba(X)[-1]
            confidence = float(probs[current_state])
            return {"regime": regime, "confidence": round(confidence, 3)}
        except Exception as e:
            logger.warning("HMM fit failed: %s", e)
            return None

    def _rule_based_regime(self, X: Optional[np.ndarray]) -> Dict:
        """Fallback when hmmlearn unavailable or HMM fails."""
        if X is None or len(X) < 5:
            return {"regime": "sideways", "confidence": 0.5}
        recent_ret = float(np.mean(X[-5:, 0]))
        recent_vix = float(np.mean(X[-5:, 1])) if X.shape[1] > 1 else 20.0
        if recent_vix > 30:
            return {"regime": "volatile", "confidence": 0.7}
        if recent_ret > 0.003:
            return {"regime": "bull", "confidence": 0.65}
        if recent_ret < -0.003:
            return {"regime": "bear", "confidence": 0.65}
        return {"regime": "sideways", "confidence": 0.6}

    def detect(self) -> Dict:
        """
        Returns current market regime (cached 30 min).
        {regime: str, confidence: float, vix: float, spy_5d_return: float}
        """
        if time.time() - self._cache["ts"] < CACHE_TTL:
            return self._cache

        X = self._fetch_features()

        result = None
        if X is not None and self._hmm_class is not None:
            result = self._fit_hmm(X)

        if result is None:
            result = self._rule_based_regime(X)

        # Enrich with macro numbers
        if X is not None and len(X) >= 5:
            result["spy_5d_return"] = round(float(np.sum(X[-5:, 0])), 4)
            result["vix"] = round(float(X[-1, 1]), 2) if X.shape[1] > 1 else None
        else:
            result["spy_5d_return"] = None
            result["vix"] = None

        result["ts"] = time.time()
        self._cache = result
        logger.info("Market regime: %s (conf=%.2f, vix=%s)", result["regime"], result["confidence"], result.get("vix"))
        return result

    def regime_context_prompt(self) -> str:
        """Returns a short string injected into LLM prompts for regime-aware analysis."""
        r = self.detect()
        vix_str = f", VIX={r['vix']}" if r.get("vix") else ""
        spy_str = f", SPY 5d={r.get('spy_5d_return', 0)*100:.2f}%" if r.get("spy_5d_return") is not None else ""
        return f"[Market regime: {r['regime'].upper()} (conf={r['confidence']:.0%}{vix_str}{spy_str})]"


# Singleton
regime_detector = RegimeDetector()
