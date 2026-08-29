"""
Retail Sentiment Service — StockTwits + Reddit (Pushshift) sentiment aggregation.
All sources are free and publicly accessible.
"""
import asyncio
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

# Reddit OAuth (optional). Without these, we fall back to the public Atom
# feed, which reddit rate-limits to roughly one request per burst per IP.
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "python:marketpulse:v1.0")

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options"]
_RSS_DELAY_SECONDS = 2.0


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
        """Try Reddit sources in order of reliability.

        RSS is first because reddit.com/search.json returns 403 to
        unauthenticated clients, and the Pushshift/PullPush mirrors are
        rate-limited (429) most of the time.
        """
        attempts = (
            ("oauth", self._reddit_via_oauth),
            ("rss", self._reddit_via_rss),
            ("pushshift", self._reddit_via_pushshift),
            ("json_api", self._reddit_via_json_api),
        )
        for name, fetch in attempts:
            try:
                msgs = await fetch(ticker)
                if msgs:
                    return {"messages": msgs, "total": len(msgs)}
                logger.debug("Reddit %s returned nothing for %s", name, ticker)
            except Exception as e:
                logger.debug("Reddit %s failed for %s: %s", name, ticker, e)
        return None

    async def _reddit_via_rss(self, ticker: str) -> list:
        """Reddit's Atom search feed — still served without authentication."""
        import xml.etree.ElementTree as ET

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        messages = []
        subreddits = SUBREDDITS
        headers = {"User-Agent": "MarketPulseOSINT/1.0"}

        async with httpx.AsyncClient(follow_redirects=True) as client:
            for idx, sub in enumerate(subreddits):
                url = (
                    f"https://www.reddit.com/r/{sub}/search.rss"
                    f"?q={ticker}&restrict_sr=1&sort=new&limit=25&t=month"
                )
                try:
                    if idx:
                        await asyncio.sleep(_RSS_DELAY_SECONDS)

                    resp = await self._get_with_backoff(client, url, headers)
                    if resp is None or resp.status_code != 200:
                        code = resp.status_code if resp is not None else "n/a"
                        logger.debug("Reddit RSS %s HTTP %s", sub, code)
                        # A 429 applies to the whole IP; further subreddits in
                        # this pass will fail too, so stop rather than burn
                        # the rate limit further.
                        if resp is not None and resp.status_code == 429:
                            break
                        continue

                    root = ET.fromstring(resp.content)
                    for entry in root.findall("atom:entry", ns):
                        title = (entry.findtext("atom:title", "", ns) or "").strip()
                        if not title:
                            continue
                        # The ticker must appear as a whole word, not as a
                        # substring of an unrelated word.
                        body_html = entry.findtext("atom:content", "", ns) or ""
                        if not re.search(rf"\b\$?{re.escape(ticker)}\b",
                                         f"{title} {body_html}", re.IGNORECASE):
                            continue

                        author = (entry.findtext("atom:author/atom:name", "", ns) or "").lstrip("/u/")
                        link_el = entry.find("atom:link", ns)
                        link = link_el.get("href", "") if link_el is not None else ""

                        messages.append({
                            "source": f"reddit/{sub}",
                            "user": author or "unknown",
                            "body": title[:280],
                            "sentiment": self._classify_sentiment(f"{title} {body_html}"),
                            "created_at": entry.findtext("atom:updated", "", ns),
                            "url": link,
                            "score": 0,
                        })
                except ET.ParseError as e:
                    logger.debug("Reddit RSS parse failed for %s: %s", sub, e)
                except Exception as e:
                    logger.debug("Reddit RSS fetch failed for %s: %s", sub, e)
        return messages

    async def _reddit_via_pushshift(self, ticker: str) -> list:
        messages = []
        subreddits = SUBREDDITS
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
        subreddits = SUBREDDITS
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

    async def _get_with_backoff(self, client, url, headers, attempts: int = 3):
        """GET with exponential backoff on 429, honouring Retry-After."""
        resp = None
        for attempt in range(attempts):
            resp = await client.get(url, headers=headers, timeout=15)
            if resp.status_code != 429:
                return resp
            if attempt == attempts - 1:
                break
            wait = float(resp.headers.get("Retry-After") or 0) or 2.0 * (2 ** attempt)
            logger.debug("Reddit 429, backing off %.1fs", wait)
            await asyncio.sleep(min(wait, 20.0))
        return resp

    async def _reddit_via_oauth(self, ticker: str) -> list:
        """Authenticated Reddit search. Needs REDDIT_CLIENT_ID/SECRET.

        This is the only Reddit path with a usable rate limit; the public
        endpoints are best-effort.
        """
        if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET):
            return []

        try:
            import praw
        except ImportError:
            logger.debug("praw not installed; skipping Reddit OAuth")
            return []

        def _search() -> list:
            reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT,
                check_for_async=False,
            )
            reddit.read_only = True
            out = []
            for sub in SUBREDDITS:
                for post in reddit.subreddit(sub).search(
                    ticker, sort="new", time_filter="week", limit=10
                ):
                    combined = f"{post.title} {getattr(post, 'selftext', '')}"
                    if not re.search(rf"\b\$?{re.escape(ticker)}\b", combined, re.IGNORECASE):
                        continue
                    out.append({
                        "source": f"reddit/{sub}",
                        "user": str(getattr(post.author, "name", "unknown")),
                        "body": post.title[:280],
                        "sentiment": self._classify_sentiment(combined),
                        "created_at": datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ).isoformat(),
                        "url": f"https://reddit.com{post.permalink}",
                        "score": int(post.score or 0),
                    })
            return out

        # praw is synchronous; keep it off the event loop.
        return await asyncio.to_thread(_search)

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
