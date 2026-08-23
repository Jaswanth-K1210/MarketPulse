"""
Earnings Transcripts Service — Parses earnings call transcripts.
Primary source is Motley Fool, which serves full transcript text without
authentication. SeekingAlpha is kept as a fallback but returns 403 to
unauthenticated clients as of 2026-08.
Extracts forward guidance tone, key metrics, and management sentiment.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FOOL_BASE = "https://www.fool.com"
FOOL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class EarningsTranscriptsService:
    async def get_transcripts(self, ticker: str, limit: int = 4) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "transcripts": [],
            "total_transcripts": 0,
            "avg_guidance_sentiment": 0,
            "avg_management_confidence": 0,
            "key_metrics": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        transcripts = await self._scrape_transcripts(ticker, limit)
        result["transcripts"] = transcripts
        result["total_transcripts"] = len(transcripts)

        if transcripts:
            sentiments = [t.get("guidance_sentiment", 0) for t in transcripts]
            confidences = [t.get("management_confidence", 0.5) for t in transcripts]

            result["avg_guidance_sentiment"] = round(sum(sentiments) / len(sentiments), 3)
            result["avg_management_confidence"] = round(sum(confidences) / len(confidences), 3)

            metrics = {}
            for t in transcripts:
                for k, v in t.get("key_metrics", {}).items():
                    if k not in metrics:
                        metrics[k] = []
                    if v is not None:
                        metrics[k].append(v)

            result["key_metrics"] = {
                k: round(sum(v) / len(v), 2) if v else None
                for k, v in metrics.items()
            }

        return result

    async def _scrape_transcripts(self, ticker: str, limit: int) -> list:
        """Fool first (works unauthenticated), SeekingAlpha as fallback."""
        try:
            transcripts = await self._scrape_fool(ticker, limit)
            if transcripts:
                return transcripts
        except Exception as e:
            logger.debug("Fool transcript scrape failed for %s: %s", ticker, e)

        try:
            return await self._scrape_seekingalpha(ticker, limit)
        except Exception as e:
            logger.debug("SeekingAlpha transcript scrape failed for %s: %s", ticker, e)
            return []

    async def _scrape_fool(self, ticker: str, limit: int) -> list:
        headers = {"User-Agent": FOOL_UA}
        links = []

        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            # The quote page lists that company's transcripts. The exchange is
            # part of the path and is not knowable up front, so try both.
            for exchange in ("nasdaq", "nyse"):
                url = f"{FOOL_BASE}/quote/{exchange}/{ticker.lower()}/"
                try:
                    resp = await client.get(url, timeout=20)
                except Exception as e:
                    logger.debug("Fool quote page %s failed: %s", url, e)
                    continue
                if resp.status_code != 200:
                    continue
                found = re.findall(r"/earnings/call-transcripts/[0-9]{4}/[0-9]{2}/[0-9]{2}/[a-z0-9\-]+/", resp.text)
                if found:
                    links = found
                    break

            if not links:
                return []

            # Slug carries the publication date; newest first.
            links = sorted(set(links), reverse=True)[:limit]

            transcripts = []
            for link in links:
                try:
                    resp = await client.get(f"{FOOL_BASE}{link}", timeout=25)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    body = soup.find("div", class_="article-body") or soup.find("article")
                    if body is None:
                        continue
                    text = body.get_text(" ", strip=True)
                    if len(text) < 500:
                        continue

                    date_match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", link)
                    transcripts.append({
                        "source": "fool",
                        "url": f"{FOOL_BASE}{link}",
                        "date": "-".join(date_match.groups()) if date_match else self._extract_date(text),
                        "text_preview": text[:1000],
                        "guidance_sentiment": self._analyze_guidance_tone(text),
                        "management_confidence": self._estimate_confidence(text),
                        "key_metrics": self._extract_key_metrics(text),
                    })
                except Exception as e:
                    logger.debug("Fool transcript %s failed: %s", link, e)
                    continue

            return transcripts

    async def _scrape_seekingalpha(self, ticker: str, limit: int) -> list:
        transcripts = []
        url = f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts"
        headers = {"User-Agent": FOOL_UA}

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                logger.debug("SeekingAlpha HTTP %s for %s", resp.status_code, ticker)
                return transcripts

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.find_all("article") or soup.find_all("div", class_=re.compile("transcript|article"))

            for article in articles[:limit]:
                text = article.get_text(strip=True)
                if len(text) > 500:
                    transcripts.append({
                        "source": "seekingalpha",
                        "url": url,
                        "date": self._extract_date(text) or "",
                        "text_preview": text[:1000],
                        "guidance_sentiment": self._analyze_guidance_tone(text),
                        "management_confidence": self._estimate_confidence(text),
                        "key_metrics": self._extract_key_metrics(text),
                    })
        return transcripts

    def _extract_date(self, text: str) -> str:
        patterns = [
            r"(\d{4}-\d{2}-\d{2})",
            r"([A-Z][a-z]+ \d{1,2}, \d{4})",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1)
        return ""

    def _analyze_guidance_tone(self, text: str) -> float:
        text_lower = text.lower()
        positive = {
            "strong", "growth", "record", "confident", "optimistic", "positive",
            "improve", "exceed", "beat", "momentum", "accelerate", "robust",
            "ahead", "upside", "outperform",
        }
        negative = {
            "challenge", "headwind", "uncertainty", "decline", "slowdown",
            "weakness", "cautious", "risk", "concern", "difficult", "delay",
            "cut", "downside", "restructuring", "reduction",
        }

        tokens = set(re.findall(r"\b\w+\b", text_lower))
        pos_hits = len(tokens & positive)
        neg_hits = len(tokens & negative)
        total = pos_hits + neg_hits or 1
        return round((pos_hits - neg_hits) / total * 2, 3)

    def _estimate_confidence(self, text: str) -> float:
        certainty = re.findall(r"\b(will|expect|confident|assure|guarantee|committed)\b", text.lower())
        uncertainty = re.findall(r"\b(may|might|could|potential|uncertain|if|depends|risk)\b", text.lower())

        base = 0.5
        base += len(certainty) * 0.02
        base -= len(uncertainty) * 0.02
        return max(0.1, min(1.0, base))

    def _extract_key_metrics(self, text: str) -> dict:
        metrics = {}

        rev_match = re.search(r"revenue\s*(?:of|:)?\s*\$?([\d,.]+)\s*(billion|million|B|M)", text.lower())
        if rev_match:
            val = float(rev_match.group(1).replace(",", ""))
            unit = rev_match.group(2)
            if unit in ("billion", "B"):
                val *= 1e9
            elif unit in ("million", "M"):
                val *= 1e6
            metrics["revenue"] = val

        eps_match = re.search(r"(?:EPS|earnings per share)\s*(?:of|:)?\s*\$?([\d,.]+)", text.lower())
        if eps_match:
            metrics["eps"] = float(eps_match.group(1).replace(",", ""))

        margin_match = re.search(r"(?:gross|profit)\s*margin\s*(?:of|:)?\s*([\d.]+)%", text.lower())
        if margin_match:
            metrics["margin_pct"] = float(margin_match.group(1))

        return metrics

    def score_earnings_sentiment(self, data: dict) -> float:
        score = 0.0
        guidance = data.get("avg_guidance_sentiment", 0)
        confidence = data.get("avg_management_confidence", 0.5)

        score += guidance * 2.0

        if confidence > 0.8:
            score += 1.0
        elif confidence > 0.6:
            score += 0.5
        elif confidence < 0.3:
            score -= 1.0

        total = data.get("total_transcripts", 0)
        if total > 2:
            score += 0.5

        return max(-5.0, min(5.0, score))


earnings_transcripts_service = EarningsTranscriptsService()
