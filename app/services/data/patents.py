"""
Patent Filings Service — USPTO patent data via PatentsView API.
Tracks patent grants, citations, and innovation velocity.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PATENTSVIEW_BASE = "https://api.patentsview.org/patents/query"


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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            query = {
                "q": {
                    "_and": [
                        {"assignee_organization": company},
                    ]
                },
                "f": [
                    "patent_number", "patent_title", "patent_date",
                    "patent_year", "cpc_group_id", "patent_abstract",
                    "citedby_count",
                ],
                "o": {"per_page": limit, "page": 1},
            }

            async with httpx.AsyncClient() as client:
                resp = await client.post(PATENTSVIEW_BASE, json=query, timeout=20)
                if resp.status_code != 200:
                    logger.warning(f"PatentsView API error: {resp.status_code}")
                    return result

                data = resp.json()
                patents = data.get("patents", [])

                for p in patents:
                    patent = {
                        "patent_number": p.get("patent_number", ""),
                        "title": p.get("patent_title", ""),
                        "date": p.get("patent_date", ""),
                        "year": p.get("patent_year", ""),
                        "abstract": (p.get("patent_abstract") or "")[:300],
                        "citations": p.get("citedby_count", 0),
                    }
                    result["patents"].append(patent)

                result["total_patents"] = len(result["patents"])

                years = {}
                cpc_counts = {}
                total_citations = 0

                for p in result["patents"]:
                    year = p.get("year")
                    if year:
                        years[year] = years.get(year, 0) + 1

                    citations = p.get("citations") or 0
                    total_citations += int(citations) if citations else 0

                result["by_year"] = dict(sorted(years.items()))
                result["recent_patents"] = result["patents"][:10]
                result["innovation_score"] = min(100, result["total_patents"] * 3 + total_citations)

        except Exception as e:
            logger.warning(f"Patents fetch failed for {company}: {e}")

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
