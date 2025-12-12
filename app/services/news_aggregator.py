"""
News Aggregator Service
Fetches news from multiple sources and filters for tracked companies
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import logging
from typing import List
from datetime import datetime, timedelta
from app.config import (
    NEWSAPI_KEY, NEWSDATA_IO_KEY, FINNHUB_API_KEY, TRACKED_COMPANIES,
    NEWSAPI_BASE_URL, NEWSDATA_BASE_URL, FINNHUB_BASE_URL,
    PORTFOLIO_COMPANIES, SUPPLY_CHAIN_COMPANIES,
    MAX_ARTICLES_PER_FETCH, GEMINI_DAILY_BUDGET, GEMINI_CALLS_PER_ARTICLE
)
from app.models.article import Article

logger = logging.getLogger(__name__)

# Global Gemini call counter for budget tracking
gemini_calls_today = 0
last_reset_date = datetime.now().date()


class NewsAggregator:
    """Aggregates news from multiple sources"""

    def __init__(self):
        """Initialize news aggregator"""
        self.seen_urls = set()  # Track seen URLs for deduplication
        logger.info("News Aggregator initialized")

    def scrape_article_content(self, url: str) -> str:
        """
        Scrape full article content from URL
        Returns full article text or empty string if scraping fails
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()

            # Try common article content containers
            article_content = None

            # Common article selectors (in order of priority)
            selectors = [
                'article',
                '[class*="article-content"]',
                '[class*="article-body"]',
                '[class*="post-content"]',
                '[class*="entry-content"]',
                '[class*="story-body"]',
                '[id*="article-content"]',
                '[id*="article-body"]',
                'main'
            ]

            for selector in selectors:
                article_content = soup.select_one(selector)
                if article_content:
                    break

            # If no article container found, get all paragraphs
            if not article_content:
                article_content = soup.find('body')

            if article_content:
                # Extract all paragraph text
                paragraphs = article_content.find_all('p')
                text = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])

                # Clean up whitespace
                text = ' '.join(text.split())

                # Only return if we got substantial content (>200 chars)
                if len(text) > 200:
                    logger.info(f"✓ Scraped {len(text)} chars from {url[:50]}...")
                    return text
                else:
                    logger.warning(f"Scraped content too short ({len(text)} chars) from {url[:50]}...")
                    return ""

            logger.warning(f"No article content found at {url[:50]}...")
            return ""

        except Exception as e:
            logger.error(f"Error scraping {url[:50]}...: {str(e)}")
            return ""

    def contains_tracked_company(self, text: str) -> bool:
        """Check if text mentions any tracked company"""
        text_lower = text.lower()
        for company in TRACKED_COMPANIES:
            if company.lower() in text_lower:
                return True
        return False

    def get_mentioned_companies(self, text: str) -> List[str]:
        """Extract which companies are mentioned in text"""
        mentioned = []
        text_lower = text.lower()
        for company in TRACKED_COMPANIES:
            if company.lower() in text_lower:
                mentioned.append(company)
        return mentioned

    def fetch_from_google_news_rss(self) -> List[Article]:
        """Fetch from Google News RSS (using summaries)"""
        articles = []
        try:
            # Google News RSS for tech news
            url = "https://news.google.com/rss/search?q=technology+OR+semiconductor+OR+chips&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            for entry in feed.entries[:20]:  # Limit to 20 recent articles
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '')

                # Skip if already seen
                if link in self.seen_urls:
                    continue

                # Check if mentions tracked companies
                full_text = f"{title} {summary}"
                if not self.contains_tracked_company(full_text):
                    continue

                # Use RSS summary as content
                content = summary

                # Skip if no substantial content
                if len(content) < 50:
                    continue

                # Get mentioned companies
                companies = self.get_mentioned_companies(full_text)
                if not companies:
                    continue

                # Parse published date
                pub_date = entry.get('published_parsed')
                if pub_date:
                    published_at = datetime(*pub_date[:6])
                else:
                    published_at = datetime.now()

                article = Article(
                    title=title,
                    url=link,
                    source="Google News",
                    published_at=published_at,
                    content=content,
                    companies_mentioned=companies
                )

                articles.append(article)
                self.seen_urls.add(link)

            logger.info(f"Fetched {len(articles)} articles from Google News RSS")

        except Exception as e:
            logger.error(f"Error fetching from Google News RSS: {str(e)}")

        return articles

    def fetch_from_newsapi(self) -> List[Article]:
        """Fetch from NewsAPI"""
        articles = []
        try:
            # Build query for tracked companies
            company_query = " OR ".join(TRACKED_COMPANIES[:5])  # Limit query length
            url = f"{NEWSAPI_BASE_URL}/everything"

            params = {
                "q": company_query,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": NEWSAPI_KEY
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get('articles', []):
                title = item.get('title', '')
                url_link = item.get('url', '')
                description = item.get('description', '') or ''
                content = item.get('content', '') or description

                # Skip if already seen
                if url_link in self.seen_urls:
                    continue

                # Check if mentions tracked companies
                full_text = f"{title} {description} {content}"
                if not self.contains_tracked_company(full_text):
                    continue

                # Parse published date
                published_at_str = item.get('publishedAt')
                if published_at_str:
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                else:
                    published_at = datetime.now()

                article = Article(
                    title=title,
                    url=url_link,
                    source=item.get('source', {}).get('name', 'NewsAPI'),
                    published_at=published_at,
                    content=content,
                    companies_mentioned=self.get_mentioned_companies(full_text)
                )

                articles.append(article)
                self.seen_urls.add(url_link)

            logger.info(f"Fetched {len(articles)} articles from NewsAPI")

        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {str(e)}")

        return articles

    def fetch_from_newsdata_io(self) -> List[Article]:
        """Fetch from NewsData.io (using summaries)"""
        articles = []
        try:
            url = f"{NEWSDATA_BASE_URL}/news"
            company_query = ",".join(TRACKED_COMPANIES[:3])  # Limit query length

            params = {
                "apikey": NEWSDATA_IO_KEY,
                "q": company_query,
                "language": "en",
                "category": "technology",
                "size": 10
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get('results', []):
                title = item.get('title', '')
                url_link = item.get('link', '')
                description = item.get('description', '') or ''
                content = item.get('content', '') or description

                # Skip if already seen
                if url_link in self.seen_urls:
                    continue

                # Check if mentions tracked companies
                full_text = f"{title} {description} {content}"
                if not self.contains_tracked_company(full_text):
                    continue

                # Skip if no substantial content
                if len(content) < 50:
                    continue

                # Get mentioned companies
                companies = self.get_mentioned_companies(full_text)
                if not companies:
                    continue

                # Parse published date
                published_at_str = item.get('pubDate')
                if published_at_str:
                    try:
                        published_at = datetime.fromisoformat(published_at_str)
                    except:
                        published_at = datetime.now()
                else:
                    published_at = datetime.now()

                article = Article(
                    title=title,
                    url=url_link,
                    source=item.get('source_id', 'NewsData.io'),
                    published_at=published_at,
                    content=content,
                    companies_mentioned=companies
                )

                articles.append(article)
                self.seen_urls.add(url_link)

            logger.info(f"Fetched {len(articles)} articles from NewsData.io")

        except Exception as e:
            logger.error(f"Error fetching from NewsData.io: {str(e)}")

        return articles

    def fetch_from_finnhub(self) -> List[Article]:
        """
        Fetch from Finnhub API
        Provides fuller article content - RECOMMENDED
        """
        articles = []

        if not FINNHUB_API_KEY:
            logger.warning("Finnhub API key not configured, skipping Finnhub fetch")
            return articles

        try:
            # Get news for each portfolio company (these are most important)
            all_tickers = {**PORTFOLIO_COMPANIES, **SUPPLY_CHAIN_COMPANIES}

            # Limit to top priority companies to avoid rate limits
            priority_companies = list(PORTFOLIO_COMPANIES.items())[:5]

            for company, ticker in priority_companies:
                try:
                    # Get news from last 7 days
                    from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                    to_date = datetime.now().strftime('%Y-%m-%d')

                    url = f"{FINNHUB_BASE_URL}/company-news"
                    params = {
                        'symbol': ticker,
                        'from': from_date,
                        'to': to_date,
                        'token': FINNHUB_API_KEY
                    }

                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    news_items = response.json()

                    # Process each news item
                    for item in news_items[:5]:  # Limit to 5 most recent per company
                        headline = item.get('headline', '')
                        url_link = item.get('url', '')
                        summary = item.get('summary', '')
                        source = item.get('source', 'Finnhub')

                        # Skip if already seen
                        if url_link in self.seen_urls:
                            continue

                        # Finnhub provides decent summaries (200-500 chars)
                        # This is much better than NewsData.io's short summaries
                        content = summary

                        # Skip if no content
                        if len(content) < 50:
                            continue

                        # Parse published date (Unix timestamp)
                        timestamp = item.get('datetime')
                        if timestamp:
                            published_at = datetime.fromtimestamp(timestamp)
                        else:
                            published_at = datetime.now()

                        # Get mentioned companies from content
                        full_text = f"{headline} {content}"
                        companies = self.get_mentioned_companies(full_text)

                        # Always include the queried company
                        if company not in companies:
                            companies.append(company)

                        article = Article(
                            title=headline,
                            url=url_link,
                            source=source,
                            published_at=published_at,
                            content=content,
                            companies_mentioned=companies
                        )

                        articles.append(article)
                        self.seen_urls.add(url_link)
                        logger.info(f"✓ Finnhub: {headline[:60]}... ({len(content)} chars)")

                    # Small delay to respect rate limits
                    import time
                    time.sleep(0.2)  # 5 requests per second max

                except Exception as e:
                    logger.error(f"Error fetching Finnhub news for {company}: {str(e)}")
                    continue

            logger.info(f"Fetched {len(articles)} articles from Finnhub")

        except Exception as e:
            logger.error(f"Error in Finnhub fetch: {str(e)}")

        return articles

    def fetch_all(self, limit: int = None) -> List[Article]:
        """
        HACKATHON MODE: Fetch from sources with hybrid interval strategy
        
        Respects Gemini free tier limit (20 RPM = ~200 calls/day)
        Strategy:
        - Every 5 min: Finnhub + Google News (no Gemini needed for initial detection)
        - Every 60 min: NewsAPI (minimal Gemini usage)
        - Every 120 min: NewsData.io (minimal Gemini usage)

        Args:
            limit: Maximum number of articles to return (default: MAX_ARTICLES_PER_FETCH = 3)
        """
        global gemini_calls_today, last_reset_date
        
        # Reset daily counter at midnight
        if datetime.now().date() > last_reset_date:
            gemini_calls_today = 0
            last_reset_date = datetime.now().date()
            logger.info("🔄 Gemini daily budget reset")
        
        # Use configured limit for hackathon
        if limit is None:
            limit = MAX_ARTICLES_PER_FETCH
        
        all_articles = []
        
        logger.info("="*70)
        logger.info(f"📊 GEMINI BUDGET: {gemini_calls_today}/{GEMINI_DAILY_BUDGET} calls used today")
        logger.info("="*70)

        # PRIORITY 1: Finnhub (safe for Gemini budget - 60/min limit)
        if FINNHUB_API_KEY and len(all_articles) < limit:
            logger.info("📰 Fetching from Finnhub (PRIMARY - safe for budget)...")
            all_articles.extend(self.fetch_from_finnhub())

        # PRIORITY 2: Google News RSS (no API limit, no Gemini cost)
        if len(all_articles) < limit:
            logger.info("📰 Fetching from Google News RSS (free - no budget impact)...")
            all_articles.extend(self.fetch_from_google_news_rss())

        # PRIORITY 3: NewsAPI only if budget allows (every 60 min in main.py)
        if NEWSAPI_KEY and len(all_articles) < limit:
            budget_remaining = GEMINI_DAILY_BUDGET - gemini_calls_today
            if budget_remaining > 10:  # Only fetch if budget available
                logger.info("📰 Fetching from NewsAPI (secondary - budget-aware)...")
                all_articles.extend(self.fetch_from_newsapi())
            else:
                logger.warning(f"⚠️ Skipping NewsAPI - Gemini budget low ({budget_remaining} calls remaining)")

        # PRIORITY 4: NewsData.io only if budget allows (every 120 min in main.py)
        if NEWSDATA_IO_KEY and len(all_articles) < limit:
            budget_remaining = GEMINI_DAILY_BUDGET - gemini_calls_today
            if budget_remaining > 5:  # Only fetch if budget available
                logger.info("📰 Fetching from NewsData.io (tertiary - budget-aware)...")
                all_articles.extend(self.fetch_from_newsdata_io())
            else:
                logger.warning(f"⚠️ Skipping NewsData.io - Gemini budget low ({budget_remaining} calls remaining)")

        # Limit to requested number
        all_articles = all_articles[:limit]

        logger.info(f"✅ Total articles fetched: {len(all_articles)} (limit: {limit})")
        logger.info(f"📊 Projected Gemini calls: ~{len(all_articles) * GEMINI_CALLS_PER_ARTICLE} (budget: {GEMINI_DAILY_BUDGET}/day)")

        return all_articles

    def clear_seen_urls(self):
        """Clear seen URLs cache"""
        self.seen_urls.clear()
        logger.info("Cleared seen URLs cache")
    
    @staticmethod
    def increment_gemini_budget(calls: int = 1):
        """Track Gemini API calls for budget management"""
        global gemini_calls_today
        gemini_calls_today += calls
        budget_remaining = GEMINI_DAILY_BUDGET - gemini_calls_today
        
        if budget_remaining < 50:
            logger.warning(f"⚠️ Gemini budget low: {budget_remaining}/{GEMINI_DAILY_BUDGET} calls remaining")
        else:
            logger.info(f"📊 Gemini budget: {gemini_calls_today}/{GEMINI_DAILY_BUDGET} calls used")
        
        return gemini_calls_today, budget_remaining
    
    @staticmethod
    def get_gemini_budget():
        """Get current Gemini budget status"""
        return gemini_calls_today, GEMINI_DAILY_BUDGET - gemini_calls_today


# Create singleton instance
news_aggregator = NewsAggregator()
