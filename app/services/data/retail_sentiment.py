"""
Retail Sentiment Service — StockTwits + Reddit (Pushshift) sentiment aggregation.
All sources are free and publicly accessible.
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

STOCKTWITS_API = "https://api.stocktwits.com/api/2"
STOCKTWITS_WEB = "https://stocktwits.com/symbol"
STOCKTWITS_API_KEY = os.environ.get("STOCKTWITS_API_KEY", "")


class RetailSentimentService:
    async def get_sentiment(self, ticker: str) -> dict:
        ticker = ticker.upper()
        result = {
            "ticker": ticker,
            "sentiment_score": 0.0,
            "bullish_pct": 0.0,
            "bearish_pct": 0.0,
            "total_mentions": 0,
            "sources": [],
            "messages": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        stocktwits = await self._get_stocktwits_sentiment(ticker)
        if stocktwits:
            result["messages"].extend(stocktwits.get("messages", []))
            result["sources"].append("stocktwits")
            result["total_mentions"] += stocktwits.get("total", 0)
        reddit = await self._get_reddit_sentiment(ticker)
        if reddit:
            result["messages"].extend(reddit.get("messages", []))
            result["sources"].append("reddit")
            result["total_mentions"] += reddit.get("total", 0)

        if result["total_mentions"] > 0:
            bullish = sum(1 for m in result["messages"] if m.get("sentiment") == "bullish")
            bearish = sum(1 for m in result["messages"] if m.get("sentiment") == "bearish")
            total = len(result["messages"])
            result["bullish_pct"] = round(bullish / total * 100, 1) if total > 0 else 0
            result["bearish_pct"] = round(bearish / total * 100, 1) if total > 0 else 0

            net = (bullish - bearish) / total if total > 0 else 0
            result["sentiment_score"] = round(net * 100, 1)

        return result

    async def _get_stocktwits_sentiment(self, ticker: str) -> Optional[dict]:
        if STOCKTWITS_API_KEY:
            return await self._stocktwits_via_api(ticker)
        result = await self._stocktwits_via_api(ticker)
        if result:
            return result
        return await self._stocktwits_via_scrape(ticker)

    async def _stocktwits_via_api(self, ticker: str) -> Optional[dict]:
        try:
            api_key = STOCKTWITS_API_KEY
            url = f"{STOCKTWITS_API}/streams/symbol/{ticker}.json"
            if api_key:
                url += f"?access_token={api_key}"
            headers = {"User-Agent": "MarketPulseOSINT/1.0", "Accept": "application/json"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
                if resp.status_code == 403 and not api_key:
                    return None
                if resp.status_code != 200:
                    return None

                data = resp.json()
                messages_raw = data.get("messages", [])
                messages = []

                for msg in messages_raw[:25]:
                    body = msg.get("body", "")
                    user = msg.get("user", {}).get("username", "anonymous")
                    created = msg.get("created_at", "")

                    sentiment = self._classify_sentiment(body)

                    messages.append({
                        "source": "stocktwits",
                        "user": user,
                        "body": body[:280],
                        "sentiment": sentiment,
                        "created_at": created,
                    })

                return {"messages": messages, "total": len(messages)}
        except Exception as e:
            logger.debug(f"StockTwits API failed for {ticker}: {e}")
            return None

    async def _stocktwits_via_scrape(self, ticker: str) -> Optional[dict]:
        try:
            url = f"{STOCKTWITS_WEB}/{ticker}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html",
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    return None

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")

                messages = []
                cards = soup.select('[data-testid="message-card"]') or soup.select(".stream-item")
                if not cards:
                    cards = soup.find_all("div", class_=re.compile("message|tweet|card"))

                for card in cards[:25]:
                    body_el = card.find("p") or card.find("div", class_=re.compile("body|content|text"))
                    if not body_el:
                        continue
                    body = body_el.get_text(strip=True)
                    if len(body) < 5:
                        continue

                    user_el = card.find("a", class_=re.compile("user|author|name"))
                    user = user_el.get_text(strip=True) if user_el else "anonymous"

                    sentiment = self._classify_sentiment(body)
                    messages.append({
                        "source": "stocktwits",
                        "user": user,
                        "body": body[:280],
                        "sentiment": sentiment,
                        "created_at": "",
                    })

                return {"messages": messages, "total": len(messages)} if messages else None
        except Exception as e:
            logger.debug(f"StockTwits scrape failed for {ticker}: {e}")
            return None

    async def _get_reddit_sentiment(self, ticker: str) -> Optional[dict]:
        messages = []
        pushshift_ok = False
        try:
            msgs = await self._reddit_via_pushshift(ticker)
            if msgs:
                messages.extend(msgs)
                pushshift_ok = True
        except Exception as e:
            logger.debug(f"Pushshift failed for {ticker}: {e}")

        if not pushshift_ok:
            try:
                msgs = await self._reddit_via_json_api(ticker)
                if msgs:
                    messages.extend(msgs)
            except Exception as e2:
                logger.debug(f"Reddit JSON API also failed for {ticker}: {e2}")

        return {"messages": messages, "total": len(messages)} if messages else None

    async def _reddit_via_pushshift(self, ticker: str) -> list:
        messages = []
        subreddits = ["wallstreetbets", "stocks", "investing", "options"]
        async with httpx.AsyncClient() as client:
            for sub in subreddits:
                try:
                    url = f"https://api.pullpush.io/reddit/submission/search?q={ticker}&subreddit={sub}&size=5&sort=desc&sort_type=created_utc"
                    headers = {"User-Agent": "MarketPulseOSINT/1.0"}
                    resp = await client.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        url = f"https://api.pushshift.io/reddit/submission/search?q={ticker}&subreddit={sub}&size=5&sort=desc&sort_type=created_utc"
                        resp = await client.get(url, headers=headers, timeout=10)
                        if resp.status_code != 200:
                            continue
                    data = resp.json()
                    for post in data.get("data", []):
                        title = post.get("title", "")
                        text = post.get("selftext", "")
                        combined = f"{title} {text}"
                        sentiment = self._classify_sentiment(combined)
                        messages.append({
                            "source": f"reddit/{sub}",
                            "user": post.get("author", "unknown"),
                            "body": title[:280],
                            "sentiment": sentiment,
                            "created_at": datetime.fromtimestamp(
                                post.get("created_utc", 0), tz=timezone.utc
                            ).isoformat(),
                            "url": f"https://reddit.com/r/{sub}/comments/{post.get('id', '')}",
                            "score": post.get("score", 0),
                        })
                except Exception:
                    continue
        return messages

    async def _reddit_via_json_api(self, ticker: str) -> list:
        messages = []
        subreddits = ["wallstreetbets", "stocks", "investing", "options"]
        async with httpx.AsyncClient() as client:
            for sub in subreddits:
                try:
                    url = f"https://www.reddit.com/r/{sub}/search.json?q={ticker}&restrict_sr=1&sort=new&limit=5&t=week"
                    headers = {"User-Agent": "MarketPulseOSINT/1.0"}
                    resp = await client.get(url, headers=headers, timeout=10)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for child in data.get("data", {}).get("children", []):
                        post = child.get("data", {})
                        title = post.get("title", "")
                        text = post.get("selftext", "")
                        combined = f"{title} {text}"
                        sentiment = self._classify_sentiment(combined)
                        messages.append({
                            "source": f"reddit/{sub}",
                            "user": post.get("author", "unknown"),
                            "body": title[:280],
                            "sentiment": sentiment,
                            "created_at": datetime.fromtimestamp(
                                post.get("created_utc", 0), tz=timezone.utc
                            ).isoformat(),
                            "url": f"https://reddit.com{post.get('permalink', '')}",
                            "score": post.get("score", 0),
                        })
                except Exception:
                    continue
        return messages

    def _classify_sentiment(self, text: str) -> str:
        text_lower = text.lower()

        bullish_words = [
            "bullish", "moon", "rocket", "buy", "long", "calls", "yolo",
            "value", "undervalued", "growth", "breakout", "support",
            "diamond hands", "hold the line", "to the moon", "price target",
            "upgrade", "overweight", "positive", "beat", "surge",
        ]
        bearish_words = [
            "bearish", "dump", "crash", "sell", "short", "puts", "overvalued",
            "decline", "downgrade", "underweight", "negative", "miss",
            "collapse", "scam", "fraud", "pump and dump", "bagholder",
            "fear", "panic", "correction", "recession",
        ]

        bull_count = sum(1 for w in bullish_words if w in text_lower)
        bear_count = sum(1 for w in bearish_words if w in text_lower)

        if bull_count > bear_count:
            return "bullish"
        elif bear_count > bull_count:
            return "bearish"
        return "neutral"

    def score_sentiment(self, data: dict) -> float:
        """Score sentiment from -5 (very bearish) to +5 (very bullish)."""
        sent_score = data.get("sentiment_score", 0)
        if sent_score == 0 and data.get("total_mentions", 0) == 0:
            return 0.0

        score = sent_score / 20.0
        return max(-5.0, min(5.0, score))


retail_sentiment_service = RetailSentimentService()
