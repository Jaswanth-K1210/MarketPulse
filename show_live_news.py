"""
Fetch and Display Live News from Finnhub
Shows news without processing (to avoid Gemini rate limits)
"""

from datetime import datetime
from app.services.news_aggregator import news_aggregator

def main():
    print("\n" + "="*80)
    print("  📰 LIVE NEWS FROM FINNHUB")
    print("="*80 + "\n")

    # Clear cache for fresh fetch
    news_aggregator.clear_seen_urls()

    # Fetch live articles
    print("Fetching latest news for portfolio companies...")
    print("Companies: AAPL, NVDA, AMD, INTC, AVGO\n")

    articles = news_aggregator.fetch_from_finnhub()

    if not articles:
        print("❌ No articles fetched")
        return

    print(f"✅ Fetched {len(articles)} live articles from Finnhub")
    print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    print("="*80)
    print("  📄 LIVE NEWS ARTICLES")
    print("="*80 + "\n")

    # Show all articles
    for i, article in enumerate(articles, 1):
        print(f"\n{'─'*80}")
        print(f"📰 ARTICLE {i}/{len(articles)}")
        print(f"{'─'*80}")
        print(f"📌 Title:     {article.title}")
        print(f"📰 Source:    {article.source}")
        print(f"🏢 Companies: {', '.join(article.companies_mentioned)}")
        print(f"📅 Published: {article.published_at}")
        print(f"🔗 URL:       {article.url}")
        print(f"\n📝 Content ({len(article.content)} chars):")
        print(f"   {article.content}")

    print(f"\n{'='*80}")
    print(f"  📊 SUMMARY")
    print(f"{'='*80}\n")

    # Company breakdown
    company_counts = {}
    for article in articles:
        for company in article.companies_mentioned:
            company_counts[company] = company_counts.get(company, 0) + 1

    print("📈 Articles per company:")
    for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {company}: {count} articles")

    # Content length stats
    lengths = [len(a.content) for a in articles]
    print(f"\n📏 Content statistics:")
    print(f"   Average length: {sum(lengths)/len(lengths):.0f} characters")
    print(f"   Shortest: {min(lengths)} characters")
    print(f"   Longest: {max(lengths)} characters")

    print(f"\n✅ Total: {len(articles)} articles fetched successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
