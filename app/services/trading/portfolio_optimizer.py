"""
Portfolio Optimizer — Black-Litterman model + risk metrics.
Combines market equilibrium with alpha score views for optimized weights.
"""
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    async def optimize(self, holdings: list, alphas: dict = None) -> dict:
        result = {
            "holdings": holdings,
            "optimized_weights": {},
            "metrics": {},
            "suggested_trades": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not holdings or len(holdings) < 2:
            result["error"] = "Need at least 2 holdings to optimize"
            return result

        tickers = [h.get("ticker", h) if isinstance(h, dict) else h for h in holdings]
        weights = self._get_current_weights(holdings)

        try:
            import yfinance as yf
            data = yf.download(tickers, period="1y", interval="1d", progress=False, auto_adjust=True)
            if data.empty or "Close" not in data.columns:
                return self._equal_weight_fallback(tickers, weights, result)

            closes = data["Close"].dropna()
            if closes.empty or len(closes.columns) < 2:
                return self._equal_weight_fallback(tickers, weights, result)

            returns = closes.pct_change().dropna()
            cov_matrix = returns.cov().values * 252

            market_weights = np.array([1 / len(tickers)] * len(tickers))
            delta = 2.5
            tau = 0.05

            pi = delta * cov_matrix @ market_weights

            if alphas:
                P = np.eye(len(tickers))
                Q = np.array([alphas.get(t, 0) / 10 for t in tickers])
                omega = np.diag([0.1] * len(tickers))

                mid = np.linalg.inv(np.linalg.inv(tau * cov_matrix) + P.T @ np.linalg.inv(omega) @ P)
                rhs = np.linalg.inv(tau * cov_matrix) @ pi + P.T @ np.linalg.inv(omega) @ Q
                bl_mean = mid @ rhs
            else:
                bl_mean = pi

            def optimize_mean_variance(mean_ret, cov):
                n = len(mean_ret)
                ones = np.ones(n)
                cov_inv = np.linalg.inv(cov + np.eye(n) * 1e-6)
                w_mvp = cov_inv @ ones / (ones.T @ cov_inv @ ones)
                return w_mvp

            opt_weights = optimize_mean_variance(bl_mean, cov_matrix)
            opt_weights = np.maximum(opt_weights, 0)
            opt_weights = opt_weights / opt_weights.sum()

            for i, t in enumerate(tickers):
                result["optimized_weights"][t] = round(float(opt_weights[i]), 4)

            port_return = float(bl_mean @ opt_weights)
            port_risk = float(np.sqrt(opt_weights @ cov_matrix @ opt_weights))

            if port_risk > 0:
                sharpe = port_return / port_risk
            else:
                sharpe = 0

            result["metrics"]["expected_return"] = round(port_return * 100, 2)
            result["metrics"]["expected_risk"] = round(port_risk * 100, 2)
            result["metrics"]["sharpe_ratio"] = round(sharpe, 3)

            for i, t in enumerate(tickers):
                current_w = weights.get(t, 0)
                new_w = opt_weights[i]
                diff = new_w - current_w
                if abs(diff) > 0.02:
                    result["suggested_trades"].append({
                        "ticker": t,
                        "action": "BUY" if diff > 0 else "SELL",
                        "current_weight": round(current_w, 3),
                        "target_weight": round(new_w, 3),
                        "adjustment": round(diff, 3),
                    })

        except Exception as e:
            logger.warning(f"Optimizer failed: {e}")
            return self._equal_weight_fallback(tickers, weights, result)

        return result

    def _get_current_weights(self, holdings: list) -> dict:
        weights = {}
        total_value = 0
        values = []

        for h in holdings:
            if isinstance(h, dict):
                t = h.get("ticker", "")
                v = h.get("value", 0) or h.get("market_value", 0) or 1
            else:
                t = h
                v = 1
            weights[t] = v
            total_value += v
            values.append(v)

        if total_value > 0:
            for t in weights:
                weights[t] /= total_value
        return weights

    def _equal_weight_fallback(self, tickers: list, weights: dict, result: dict) -> dict:
        n = len(tickers)
        ew = 1.0 / n
        for t in tickers:
            result["optimized_weights"][t] = round(ew, 4)
        result["metrics"] = {
            "expected_return": 0,
            "expected_risk": 0,
            "sharpe_ratio": 0,
            "note": "Equal weight fallback (insufficient data)",
        }
        return result

    async def calculate_risk_metrics(self, tickers: list) -> dict:
        result = {"tickers": tickers, "metrics": {}, "timestamp": datetime.now(timezone.utc).isoformat()}

        try:
            import yfinance as yf
            data = yf.download(tickers, period="1y", interval="1d", progress=False, auto_adjust=True)
            if data.empty:
                return result

            closes = data["Close"].dropna()
            returns = closes.pct_change().dropna()

            equal_weights = np.array([1 / len(tickers)] * len(tickers))
            port_returns = returns @ equal_weights

            if len(port_returns) > 0:
                result["metrics"]["var_95"] = round(float(np.percentile(port_returns, 5) * 100), 2)
                result["metrics"]["cvar_95"] = round(float(port_returns[port_returns <= np.percentile(port_returns, 5)].mean() * 100), 2)
                result["metrics"]["max_drawdown"] = round(float((port_returns.cumsum().cummax() - port_returns.cumsum()).max() * 100), 2)

            rf = 0.05 / 252
            excess = port_returns - rf
            if excess.std() > 0:
                result["metrics"]["sharpe_annual"] = round(float(excess.mean() / excess.std() * np.sqrt(252)), 3)

            for t in tickers:
                if t in returns.columns:
                    t_ret = returns[t]
                    beta = t_ret.cov(port_returns) / port_returns.var() if port_returns.var() > 0 else 1
                    result["metrics"][f"{t}_beta"] = round(float(beta), 3)

        except Exception as e:
            logger.warning(f"Risk metrics failed: {e}")

        return result


portfolio_optimizer = PortfolioOptimizer()
