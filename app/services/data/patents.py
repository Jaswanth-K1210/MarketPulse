"""
Patent Filings Service — USPTO patent data.

The legacy PatentsView endpoint (api.patentsview.org) was retired and now
301s to USPTO's transition guide. Its replacement, PatentsView Search,
requires a free API key. Set PATENTSVIEW_API_KEY to enable this service;
without it the service reports itself unavailable rather than returning
zeros that look like a real "no patents" answer.

Key registration: https://patentsview.org/apis/keyrequest
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PATENTSVIEW_BASE = "https://search.patentsview.org/api/v1/patent/"
PATENTSVIEW_API_KEY = os.environ.get("PATENTSVIEW_API_KEY", "")


class PatentsService:
    async def get_patents(self, company: str, limit: int = 50) -> dict:
        result = {
            "company": company,
            "patents": [],
            "total_patents": 0,
            "recent_patents": [],
            "by_year": {},
            "top_cpc_codes": [],
            "innovation_score": 0,
            "available": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if not PATENTSVIEW_API_KEY:
            result["error"] = (
                "PATENTSVIEW_API_KEY not set — PatentsView requires a free API key "
                "since the legacy endpoint was retired. Request one at "
                "https://patentsview.org/apis/keyrequest"
            )
            logger.info("Patents service disabled: no PATENTSVIEW_API_KEY")
            return result

        try:
            params = {
                "q": json.dumps({"assignees.assignee_organization": company}),
                "f": json.dumps([
                    "patent_id", "patent_title", "patent_date",
                    "patent_abstract",
                ]),
                "o": json.dumps({"size": min(limit, 100)}),
            }
            headers = {"X-Api-Key": PATENTSVIEW_API_KEY}

            async with httpx.AsyncClient() as client:
                resp = await client.get(PATENTSVIEW_BASE, params=params,
                                        headers=headers, timeout=25)
                if resp.status_code != 200:
                    logger.warning("PatentsView API error: %s", resp.status_code)
                    result["error"] = f"PatentsView returned HTTP {resp.status_code}"
                    return result

                data = resp.json()
                result["available"] = True

                for p in data.get("patents", []):
                    date = p.get("patent_date", "") or ""
                    result["patents"].append({
                        "patent_number": p.get("patent_id", ""),
                        "title": p.get("patent_title", ""),
                        "date": date,
                        "year": date[:4] if date else "",
                        "abstract": (p.get("patent_abstract") or "")[:300],
                        "citations": 0,
                    })

                result["total_patents"] = data.get("total_hits", len(result["patents"]))

                years = {}
                total_citations = 0
                for p in result["patents"]:
                    year = p.get("year")
                    if year:
                        years[year] = years.get(year, 0) + 1
                    total_citations += int(p.get("citations") or 0)

                result["by_year"] = dict(sorted(years.items()))
                result["recent_patents"] = result["patents"][:10]
                result["innovation_score"] = min(
                    100, len(result["patents"]) * 3 + total_citations
                )

        except Exception as e:
            logger.warning("Patents fetch failed for %s: %s", company, e)
            result["error"] = str(e)

        return result

    def score_patent_activity(self, data: dict) -> float:
        score = 0.0
        total = data.get("total_patents", 0)

        if total > 30:
            score += 2.5
        elif total > 15:
            score += 1.5
        elif total > 5:
            score += 0.5

        recent = data.get("recent_patents", [])
        if recent:
            current_year = datetime.now().year
            recent_count = sum(1 for p in recent if str(p.get("year", "")) == str(current_year))
            if recent_count >= 3:
                score += 1.5
            elif recent_count >= 1:
                score += 0.5

        innovation = data.get("innovation_score", 0)
        if innovation > 80:
            score += 1.0
        elif innovation > 50:
            score += 0.5

        return max(-5.0, min(5.0, score))


patents_service = PatentsService()
