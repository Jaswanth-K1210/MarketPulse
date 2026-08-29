"""
Twitter/X Sentiment Service — Searches public Twitter/X for ticker mentions.

Uses Nitter instances, which no longer reliably serve search results: as of
2026-08 nitter.net returns 200 with an empty timeline and the other public
instances return 403. The service therefore reports itself unavailable
rather than returning zeros that look like genuine silence. Set
NITTER_INSTANCES (comma-separated) to point at a working/self-hosted instance.
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_DEFAULT_NITTER = "https://nitter.net,https://nitter.poast.org,https://nitter.lacontrevoie.fr"
NITTER_INSTANCES = [
    i.strip() for i in os.environ.get("NITTER_INSTANCES", _DEFAULT_NITTER).split(",") if i.strip()
]

TWITTER_HASHTAGS = {
    "$TSLA", "$AAPL", "$NVDA", "$AMD", "$MSFT", "$GOOGL", "$GOOG", "$META",
    "$AMZN", "$INTC", "$TSM", "$QQQ", "$SPY", "$GME", "$AMC", "$PLTR",
    "$SOFI", "$RIVN", "$NIO", "$BABA", "$BA", "$CAT", "$JPM", "$GS",
}


class TwitterSentimentService:
    async def get_sentiment(self, ticker: str, hours_back: int = 24) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "mentions": [],
            "total_mentions": 0,
            "positive_mentions": 0,
            "negative_mentions": 0,
            "neutral_mentions": 0,
            "bullish_pct": 0,
            "bearish_pct": 0,
            "avg_sentiment": 0,
            "top_hashtags": [],
            "available": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        mentions = await self._search_nitter(ticker)
        if not mentions:
            result["error"] = (
                "No Nitter instance returned results. Public instances are "
                "largely defunct; set NITTER_INSTANCES to a working instance."
            )
            return result

        result["available"] = True

        result["mentions"] = mentions[:50]
        result["total_mentions"] = len(mentions)

        positive = negative = neutral = 0
        total_score = 0

        for m in mentions:
            score = m.get("sentiment_score", 0)
            if score > 0.15:
                positive += 1
            elif score < -0.15:
                negative += 1
            else:
                neutral += 1
            total_score += score

        result["positive_mentions"] = positive
        result["negative_mentions"] = negative
        result["neutral_mentions"] = neutral

        total = len(mentions) or 1
        result["bullish_pct"] = round(positive / total * 100, 1)
        result["bearish_pct"] = round(negative / total * 100, 1)
        result["avg_sentiment"] = round(total_score / total, 3)

        hashtags = self._extract_hashtags(mentions)
        result["top_hashtags"] = hashtags[:10]

        return result

    async def _search_nitter(self, ticker: str) -> list:
        mentions = []
        nitter_instances = NITTER_INSTANCES

        query = f"${ticker} OR #{ticker} OR {ticker} stock"

        for instance in nitter_instances:
            try:
                url = f"{instance}/search?q={query}&f=tweets"
                headers = {"User-Agent": "Mozilla/5.0"}
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, headers=headers, timeout=10, follow_redirects=True)
                    if resp.status_code != 200:
                        continue

                    soup = BeautifulSoup(resp.text, "html.parser")
                    tweets = soup.find_all("div", class_="tweet-content")

                    for tweet in tweets[:80]:
                        text = tweet.get_text(strip=True)
                        if text and len(text) > 10:
                            mentions.append({
                                "text": text[:280],
                                "source": instance,
                                "sentiment_score": self._keyword_sentiment(text),
                            })

                    if mentions:
                        break
            except Exception as e:
                logger.debug(f"Nitter {instance} failed: {e}")
                continue

        return mentions

    def _keyword_sentiment(self, text: str) -> float:
        text_lower = text.lower()

        positive_words = {
            "bullish", "moon", "rocket", "buy", "profit", "surge", "breakout",
            "green", "gain", "growth", "strong", "beat", "upgrade", "positive",
            "catalyst", "support", "momentum", "accumulate",
        }
        negative_words = {
            "bearish", "dump", "sell", "crash", "loss", "decline", "red",
            "plunge", "drop", "falling", "weak", "downgrade", "negative",
            "resistance", "reversal", "panic", "short", "overvalued", "risk",
        }

        tokens = set(re.findall(r"\b\w+\b", text_lower))
        pos_hits = len(tokens & positive_words)
        neg_hits = len(tokens & negative_words)
        total = pos_hits + neg_hits or 1
        return round((pos_hits - neg_hits) / total, 3)

    def _extract_hashtags(self, mentions: list) -> list:
        tag_counts = {}
        for m in mentions:
            tags = re.findall(r"#(\w+)", m.get("text", ""))
            cashtags = re.findall(r"\$([A-Z]+)", m.get("text", ""))
            for t in tags + cashtags:
                tag_counts[t.upper()] = tag_counts.get(t.upper(), 0) + 1

        return sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def score_twitter_sentiment(self, data: dict) -> float:
        score = 0.0
        bullish = data.get("bullish_pct", 0)
        bearish = data.get("bearish_pct", 0)
        total = data.get("total_mentions", 0)

        if total == 0:
            return 0.0

        net_sentiment = bullish - bearish

        if net_sentiment > 30:
            score += 2.5
        elif net_sentiment > 15:
            score += 1.5
        elif net_sentiment > 5:
            score += 0.5
        elif net_sentiment < -30:
            score -= 2.5
        elif net_sentiment < -15:
            score -= 1.5
        elif net_sentiment < -5:
            score -= 0.5

        if total > 100:
            score += 0.5
        elif total > 50:
            score += 0.25

        avg_sent = data.get("avg_sentiment", 0)
        score += avg_sent * 2

        return max(-5.0, min(5.0, score))


twitter_sentiment_service = TwitterSentimentService()
