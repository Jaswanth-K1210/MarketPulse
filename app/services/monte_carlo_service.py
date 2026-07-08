"""
Monte Carlo Portfolio Risk Simulator
=====================================
Runs N Geometric Brownian Motion (GBM) simulations over a 48-hour horizon.
GNN shock scores are injected as drift adjustments so the simulation reflects
the supply-chain impact, not just base-rate market randomness.

Usage:
    from app.services.monte_carlo_service import monte_carlo
    result = monte_carlo.simulate(portfolio, gnn_impacts, current_prices)
"""
import logging
import time
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Per-ticker historical vol estimates (annualised σ) ─────────────────────────
# Used when live vol data isn't available.  Source: 90-day realised vol as of 2025.
_DEFAULT_VOL: Dict[str, float] = {
    "AAPL": 0.24, "NVDA": 0.55, "AMD":  0.55, "INTC": 0.35,
    "TSM":  0.30, "MSFT": 0.22, "GOOGL":0.25, "META": 0.35,
    "AMZN": 0.30, "TSLA": 0.65, "AVGO": 0.35, "QCOM": 0.38,
    "ASML": 0.32, "BA":   0.38, "GE":   0.30, "RTX":  0.25,
    "XOM":  0.25, "CVX":  0.25, "MU":   0.50, "CSCO": 0.22,
}
_DEFAULT_ANNUAL_VOL  = 0.35   # fallback if ticker not in table
_TRADING_HOURS_YEAR  = 252 * 6.5   # ~1638 trading hours per year
_HOURLY_DT           = 1 / _TRADING_HOURS_YEAR


def _annual_to_hourly_vol(annual_vol: float) -> float:
    return annual_vol * np.sqrt(_HOURLY_DT)


def _gnn_to_drift_bias(gnn_pct: float) -> float:
    """
    Convert a GNN impact percentage to an hourly drift bias.
    A -10 % GNN impact spreads as a -10%/48h expected drift over the horizon.
    """
    return (gnn_pct / 100) / 48   # per-hour drift adjustment


class MonteCarloService:

    def __init__(self, n_simulations: int = 2000, horizon_hours: int = 48):
        self.n         = n_simulations
        self.horizon   = horizon_hours

    def simulate(
        self,
        portfolio: List[str],
        gnn_impacts: Dict[str, float],      # percent impact per ticker from GNN
        current_prices: Optional[Dict[str, float]] = None,
        risk_threshold: float = -2.0,       # flag if P&L < -2 %
        vol_overrides: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Run GBM Monte Carlo for each portfolio ticker, then aggregate.

        Returns a rich dict consumed by Agent 6 and the /api/intelligence/monte-carlo endpoint.
        """
        t0 = time.perf_counter()
        rng = np.random.default_rng()

        prices    = current_prices or {}
        vol_ovr   = vol_overrides  or {}
        per_ticker: Dict[str, dict] = {}
        portfolio_pnl = np.zeros(self.n)   # equal-weight

        for ticker in portfolio:
            px = prices.get(ticker, 100.0) or 100.0

            # Annualised vol → hourly vol
            ann_vol  = vol_ovr.get(ticker) or _DEFAULT_VOL.get(ticker, _DEFAULT_ANNUAL_VOL)
            hrly_vol = _annual_to_hourly_vol(ann_vol)

            # GNN-adjusted drift per hour
            gnn_pct  = gnn_impacts.get(ticker, 0.0)
            mu_hour  = _gnn_to_drift_bias(gnn_pct)

            # GBM: log-returns over `horizon` hours
            # r_t = (mu - σ²/2)·dt + σ·√dt·Z_t
            Z           = rng.standard_normal((self.n, self.horizon))
            log_returns = (mu_hour - 0.5 * hrly_vol**2) + hrly_vol * Z
            cum_returns = log_returns.sum(axis=1)           # total over horizon
            end_prices  = px * np.exp(cum_returns)
            pct_returns = (end_prices - px) / px * 100.0   # percent

            # Risk metrics
            var_95  = float(np.percentile(pct_returns, 5))
            tail    = pct_returns[pct_returns <= var_95]
            cvar_95 = float(np.mean(tail)) if len(tail) > 0 else var_95

            per_ticker[ticker] = {
                "expected_return_pct": round(float(np.mean(pct_returns)), 3),
                "std_dev_pct":         round(float(np.std(pct_returns)),  3),
                "var_95_pct":          round(var_95,   3),   # 95 % Value-at-Risk
                "cvar_95_pct":         round(cvar_95,  3),   # Conditional VaR (Expected Shortfall)
                "prob_any_loss_pct":   round(float(np.mean(pct_returns < 0)  * 100), 2),
                "prob_below_threshold":round(float(np.mean(pct_returns < risk_threshold) * 100), 2),
                "gnn_shock_pct":       round(gnn_pct, 2),
                "annual_vol_used":     round(ann_vol * 100, 1),
                "current_price":       round(px, 2),
                # Scenario buckets
                "scenario_p10":        round(float(np.percentile(pct_returns, 10)), 2),
                "scenario_p50":        round(float(np.percentile(pct_returns, 50)), 2),
                "scenario_p90":        round(float(np.percentile(pct_returns, 90)), 2),
            }
            portfolio_pnl += pct_returns / max(len(portfolio), 1)

        # Portfolio-level aggregate
        port_var   = float(np.percentile(portfolio_pnl, 5))
        port_tail  = portfolio_pnl[portfolio_pnl <= port_var]
        port_cvar  = float(np.mean(port_tail)) if len(port_tail) > 0 else port_var

        severity = (
            "critical" if port_var < -5
            else "high"    if port_var < -2
            else "medium"  if port_var < 0
            else "low"
        )

        elapsed = round(time.perf_counter() - t0, 3)
        logger.info(
            "Monte Carlo: %d sims × %dh | VaR-95 %.2f%% | CVaR-95 %.2f%% | %.3fs",
            self.n, self.horizon, port_var, port_cvar, elapsed,
        )

        return {
            "n_simulations":         self.n,
            "horizon_hours":         self.horizon,
            "risk_threshold_pct":    risk_threshold,
            "portfolio": {
                "expected_return_pct": round(float(np.mean(portfolio_pnl)), 3),
                "std_dev_pct":         round(float(np.std(portfolio_pnl)),  3),
                "var_95_pct":          round(port_var,  3),
                "cvar_95_pct":         round(port_cvar, 3),
                "prob_any_loss_pct":   round(float(np.mean(portfolio_pnl < 0)                    * 100), 2),
                "prob_below_threshold":round(float(np.mean(portfolio_pnl < risk_threshold)       * 100), 2),
                "severity":            severity,
                "scenario_p10":        round(float(np.percentile(portfolio_pnl, 10)), 2),
                "scenario_p50":        round(float(np.percentile(portfolio_pnl, 50)), 2),
                "scenario_p90":        round(float(np.percentile(portfolio_pnl, 90)), 2),
            },
            "per_ticker":  per_ticker,
            "elapsed_s":   elapsed,
        }

    def stress_test(
        self,
        portfolio: List[str],
        scenarios: List[Dict],
        current_prices: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Run multiple named scenarios (e.g. Taiwan conflict, oil shock) and compare VaR.
        Each scenario is {"name": str, "shocks": {ticker: pct_impact}}.
        """
        results = {}
        for scenario in scenarios:
            name   = scenario.get("name", "unnamed")
            shocks = scenario.get("shocks", {})
            results[name] = self.simulate(portfolio, shocks, current_prices)["portfolio"]
        return results


# ── Module-level singleton ─────────────────────────────────────────────────────
monte_carlo = MonteCarloService(n_simulations=2000, horizon_hours=48)

# ── Predefined geopolitical stress scenarios ───────────────────────────────────
STRESS_SCENARIOS = [
    {
        "name": "Taiwan Strait Crisis",
        "shocks": {"TSM": -50.0, "AAPL": -25.0, "NVDA": -30.0, "AMD": -20.0, "ASML": -20.0},
    },
    {
        "name": "US-China Chip Ban Escalation",
        "shocks": {"NVDA": -35.0, "AMD": -20.0, "ASML": -15.0, "QCOM": -25.0},
    },
    {
        "name": "Global Oil Shock (+40%)",
        "shocks": {"XOM": +20.0, "CVX": +18.0, "BA": -15.0, "AMZN": -8.0, "GOOGL": -5.0},
    },
    {
        "name": "AI Bubble Correction",
        "shocks": {"NVDA": -40.0, "META": -25.0, "MSFT": -15.0, "GOOGL": -20.0, "AMD": -30.0},
    },
]
