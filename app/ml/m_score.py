"""
Beneish M-Score — Detects earnings manipulation.
8 financial ratios: DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA.
M-Score > -2.22 = likely manipulator. M-Score < -2.22 = unlikely manipulator.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class BeneishMScore:
    async def calculate(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "m_score": None,
            "manipulation_likelihood": "unknown",
            "components": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)
            bs = stock.balance_sheet
            inc = stock.income_stmt
            cf = stock.cashflow

            if bs.empty or inc.empty or cf.empty:
                logger.warning(f"Insufficient financial data for {ticker}")
                return result

            bs_cols = bs.columns[:2]
            inc_cols = inc.columns[:2]
            cf_cols = cf.columns[:2]

            if len(bs_cols) < 2 or len(inc_cols) < 2:
                return result

            curr_bs, prev_bs = [bs.get(c, {}).fillna(0) for c in bs_cols[:2]]
            curr_inc, prev_inc = [inc.get(c, {}).fillna(0) for c in inc_cols[:2]]
            curr_cf, prev_cf = [cf.get(c, {}).fillna(0) for c in cf_cols[:2]]

            def safe_val(series, key, default=0):
                try:
                    v = series.get(key, default)
                    if isinstance(v, (int, float)) and v != 0:
                        return v
                    return default
                except Exception:
                    return default

            ar_curr = safe_val(curr_bs, "Accounts Receivable")
            ar_prev = safe_val(prev_bs, "Accounts Receivable")
            rev_curr = safe_val(curr_inc, "Total Revenue")
            rev_prev = safe_val(prev_inc, "Total Revenue")

            cogs_curr = safe_val(curr_inc, "Cost Of Revenue")
            cogs_prev = safe_val(prev_inc, "Cost Of Revenue")

            assets_curr = safe_val(curr_bs, "Total Assets")
            assets_prev = safe_val(prev_bs, "Total Assets")

            ppe_curr = safe_val(curr_bs, "Property Plant Equipment")
            ppe_prev = safe_val(prev_bs, "Property Plant Equipment")

            dep_curr = safe_val(curr_cf, "Depreciation And Amortization")
            dep_prev = safe_val(prev_cf, "Depreciation And Amortization")

            sga_curr = safe_val(curr_inc, "Selling General And Administration")
            sga_prev = safe_val(prev_inc, "Selling General And Administration")

            lt_debt_curr = safe_val(curr_bs, "Long Term Debt")
            lt_debt_prev = safe_val(prev_bs, "Long Term Debt")

            cur_assets_curr = safe_val(curr_bs, "Current Assets")
            cur_assets_prev = safe_val(prev_bs, "Current Assets")
            cur_liab_curr = safe_val(curr_bs, "Current Liabilities")
            cur_liab_prev = safe_val(prev_bs, "Current Liabilities")

            ni_curr = safe_val(curr_inc, "Net Income")
            cfo_curr = safe_val(curr_cf, "Operating Cash Flow")
            cfo_prev = safe_val(prev_cf, "Operating Cash Flow")

            def ratio_or_zero(num, den):
                return num / den if den != 0 else 0

            dsri = ratio_or_zero(ar_curr / rev_curr, ar_prev / rev_prev) if rev_curr and rev_prev else 1
            gmi = ratio_or_zero(cogs_prev / rev_prev, cogs_curr / rev_curr) if rev_curr and rev_prev and cogs_curr and cogs_prev else 1
            aqi = ratio_or_zero(
                1 - (cur_assets_curr + ppe_curr) / assets_curr,
                1 - (cur_assets_prev + ppe_prev) / assets_prev,
            ) if assets_curr and assets_prev else 1
            sgi = ratio_or_zero(rev_curr, rev_prev) if rev_prev else 1
            depi = ratio_or_zero(dep_prev / assets_prev, dep_curr / assets_curr) if assets_curr and assets_prev else 1
            sgai = ratio_or_zero(sga_curr / rev_curr, sga_prev / rev_prev) if rev_curr and rev_prev else 1
            lvgi = ratio_or_zero(
                (lt_debt_curr + cur_liab_curr) / assets_curr,
                (lt_debt_prev + cur_liab_prev) / assets_prev,
            ) if assets_curr and assets_prev else 1

            working_cap_curr = cur_assets_curr - cur_liab_curr
            working_cap_prev = cur_assets_prev - cur_liab_prev
            delta_wc = working_cap_curr - working_cap_prev
            tata = ratio_or_zero(ni_curr - cfo_curr, assets_curr) if assets_curr else 0

            m_score = (
                -4.840
                + 0.920 * dsri
                + 0.528 * gmi
                + 0.404 * aqi
                + 0.892 * sgi
                + 0.115 * depi
                - 0.172 * sgai
                + 4.679 * tata
                - 0.327 * lvgi
            )

            result["m_score"] = round(m_score, 4)
            result["manipulation_likelihood"] = "likely" if m_score > -2.22 else "unlikely"
            result["components"] = {
                "dsri": round(dsri, 4),
                "gmi": round(gmi, 4),
                "aqi": round(aqi, 4),
                "sgi": round(sgi, 4),
                "depi": round(depi, 4),
                "sgai": round(sgai, 4),
                "lvgi": round(lvgi, 4),
                "tata": round(tata, 4),
            }

        except Exception as e:
            logger.warning(f"Beneish M-Score failed for {ticker}: {e}")

        return result


beneish_m_score = BeneishMScore()
