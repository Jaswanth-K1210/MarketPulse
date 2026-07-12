"""
Altman Z-Score — Bankruptcy prediction from financial statements.
Z > 2.99 = Safe, 1.81 < Z < 2.99 = Grey, Z < 1.81 = Distress.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class AltmanZScore:
    async def calculate(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "z_score": None,
            "zone": "unknown",
            "components": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)
            bs = stock.balance_sheet
            inc = stock.income_stmt

            if bs.empty or inc.empty:
                logger.warning(f"Insufficient financial data for {ticker}")
                return result

            cols = bs.columns[:1]
            inc_cols = inc.columns[:1]

            if not cols or not inc_cols:
                return result

            bs_data = bs.get(cols[0], {}).fillna(0)
            inc_data = inc.get(inc_cols[0], {}).fillna(0)

            def val(key, default=0):
                try:
                    v = bs_data.get(key, default)
                    if isinstance(v, (int, float)) and v != 0:
                        return v
                    return default
                except Exception:
                    return default

            def inc_val(key, default=0):
                try:
                    v = inc_data.get(key, default)
                    if isinstance(v, (int, float)) and v != 0:
                        return v
                    return default
                except Exception:
                    return default

            working_capital = val("Current Assets") - val("Current Liabilities")
            total_assets = val("Total Assets")
            retained_earnings = val("Retained Earnings")
            ebit = inc_val("EBIT") or inc_val("Operating Income")
            market_cap = None
            total_liabilities = val("Total Liabilities") or val("Total Debt Net Minority")

            try:
                stock_info = stock.info
                market_cap = stock_info.get("marketCap")
            except Exception:
                pass

            if not total_assets:
                return result

            x1 = working_capital / total_assets
            x2 = retained_earnings / total_assets if retained_earnings else 0
            x3 = ebit / total_assets if ebit else 0

            if market_cap and total_liabilities:
                x4 = market_cap / total_liabilities
            else:
                x4 = 0

            if total_assets:
                rev = inc_val("Total Revenue")
                x5 = rev / total_assets if rev else 0
            else:
                x5 = 0

            z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

            if z_score > 2.99:
                zone = "safe"
            elif z_score > 1.81:
                zone = "grey"
            else:
                zone = "distress"

            result["z_score"] = round(z_score, 4)
            result["zone"] = zone
            result["components"] = {
                "x1_working_capital_ratio": round(x1, 4),
                "x2_retained_earnings_ratio": round(x2, 4),
                "x3_ebit_ratio": round(x3, 4),
                "x4_market_equity_ratio": round(x4, 4),
                "x5_revenue_ratio": round(x5, 4),
            }

        except Exception as e:
            logger.warning(f"Altman Z-Score failed for {ticker}: {e}")

        return result


altman_z_score = AltmanZScore()
