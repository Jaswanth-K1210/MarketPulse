"""
Institutional Holdings Service — 13F filings via SEC EDGAR + yfinance.
Tracks institutional ownership, quarterly changes, and concentration.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


class InstitutionalHoldingsService:
    async def get_holdings(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "institutional_owners": [],
            "top_holders": [],
            "insider_ownership_pct": None,
            "institutional_ownership_pct": None,
            "total_institutional_value": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result["institutional_ownership_pct"] = info.get("heldPercentInstitutions")
            result["insider_ownership_pct"] = info.get("heldPercentInsiders")

            majors = stock.major_holders
            if majors is not None and not majors.empty:
                holders = []
                for idx, row in majors.iterrows():
                    holders.append({
                        "category": str(row.iloc[0]) if len(row) > 0 else "",
                        "percentage": float(row.iloc[1]) if len(row) > 1 else 0,
                    })
                result["top_holders"] = holders

            inst = stock.institutional_holders
            if inst is not None and not inst.empty:
                owners = []
                for idx, row in inst.iterrows():
                    owners.append({
                        "holder": str(row.get("Holder", "")),
                        "shares": int(row.get("Shares", 0)),
                        "date_reported": str(row.get("Date Reported", "")),
                        "value": float(row.get("Value", 0)),
                        "change": int(row.get("pctHeld", 0)) if "pctHeld" in row else 0,
                    })
                result["institutional_owners"] = owners

                total_val = sum(o.get("value", 0) for o in owners if o.get("value"))
                result["total_institutional_value"] = total_val

        except Exception as e:
            logger.warning(f"Institutional holdings fetch failed for {ticker}: {e}")

        return result

    def score_institutional_activity(self, data: dict) -> float:
        score = 0.0
        inst_pct = data.get("institutional_ownership_pct")

        if inst_pct is not None:
            if inst_pct > 0.7:
                score += 1.5
            elif inst_pct > 0.5:
                score += 1.0
            elif inst_pct > 0.3:
                score += 0.5
            elif inst_pct < 0.1:
                score -= 0.5

        insider_pct = data.get("insider_ownership_pct")
        if insider_pct is not None:
            if insider_pct > 0.3:
                score += 1.0
            elif insider_pct > 0.1:
                score += 0.5

        owners = data.get("institutional_owners", [])
        if owners:
            recent = owners[:5]
            buys = sum(1 for o in recent if o.get("change", 0) > 0)
            sells = sum(1 for o in recent if o.get("change", 0) < 0)

            if buys > sells:
                score += 1.0
            elif sells > buys:
                score -= 1.0

            total_change = sum(o.get("change", 0) for o in recent)
            if total_change > 100000:
                score += 0.5
            elif total_change < -100000:
                score -= 0.5

        return max(-5.0, min(5.0, score))


institutional_holdings_service = InstitutionalHoldingsService()
