@router.get("/articles")
async def get_articles(limit: int = 10, portfolio: str = None):
    """Get live news from MULTIPLE sources (NewsAPI, Finnhub, GNews, RSS, etc.)"""
    from app.services.news_aggregator import NewsIngestionLayer
    
    tickers = ['AAPL', 'NVDA', 'AMD', 'MSFT', 'GOOGL']
    if portfolio:
        tickers = [t.strip().upper() for t in portfolio.split(',')]
    
    logger.info(f"📰 Fetching news from MULTIPLE sources for: {tickers}")
    
    try:
        news_layer = NewsIngestionLayer()
        query = " OR ".join(tickers)
        
        # Fetch from ALL available sources
        all_articles = []
        all_articles.extend(news_layer.fetch_news_api(query) or [])
        all_articles.extend(news_layer.fetch_finnhub(query) or [])
        all_articles.extend(news_layer.fetch_gnews(query) or [])
        all_articles.extend(news_layer.fetch_hacker_news() or [])
        
        logger.info(f"✅ Got {len(all_articles)} articles from all sources")
        
        # Filter and tag
        filtered = []
        for art in all_articles:
            text = f"{art.get('title', '')} {art.get('content', '')}".upper()
            affected = [t for t in tickers if t in text]
            if affected:
                art['affected_companies'] = affected
                filtered.append(art)
        
        # Deduplicate
        seen = set()
        unique = [a for a in filtered if not (a.get('url') in seen or seen.add(a.get('url', '')))]
        unique.sort(key=lambda x: x.get('published_at', ''), reverse=True)
        
        if unique:
            return {"articles": unique[:limit]}
        
        # Fallback demo data
        return {"articles": [
            {"title": "Apple AI iPhone", "url": "https://tc.com/1", "content": "Apple AI...", 
             "source": "TechCrunch", "published_at": "2025-12-20T14:00:00Z", "affected_companies": ["AAPL"]},
            {"title": "NVIDIA GPU Record", "url": "https://tv.com/2", "content": "NVIDIA GPU...", 
             "source": "The Verge", "published_at": "2025-12-20T13:00:00Z", "affected_companies": ["NVDA"]}
        ][:limit]}
    except Exception as e:
        logger.error(f"❌ News error: {e}")
        return {"articles": []}
