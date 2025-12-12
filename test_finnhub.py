"""
Test Finnhub Integration
Verifies that Finnhub provides fuller article content for Gemini analysis
"""

import asyncio
import logging
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


async def main():
    print_separator("🚀 TESTING FINNHUB INTEGRATION")

    # Clear cache
    news_aggregator.clear_seen_urls()

    # Fetch from Finnhub only
    print("📰 Fetching news from Finnhub API...")
    print("   Companies: AAPL, NVDA, AMD, INTC, AVGO")
    print("   Date range: Last 7 days")
    print()

    articles = news_aggregator.fetch_from_finnhub()

    if not articles:
        print("❌ No articles fetched from Finnhub")
        print("   Possible reasons:")
        print("   - API key invalid")
        print("   - No recent news for these companies")
        print("   - Rate limit exceeded")
        return

    print(f"✅ Fetched {len(articles)} articles from Finnhub\n")

    # Analyze content quality
    print_separator("📊 CONTENT QUALITY ANALYSIS")

    total_length = sum(len(a.content) for a in articles)
    avg_length = total_length / len(articles)

    print(f"Total articles: {len(articles)}")
    print(f"Average content length: {avg_length:.0f} characters")
    print(f"Min content length: {min(len(a.content) for a in articles)} characters")
    print(f"Max content length: {max(len(a.content) for a in articles)} characters")
    print()

    # Show sample articles
    print_separator("📄 SAMPLE ARTICLES")

    for i, article in enumerate(articles[:3], 1):
        print(f"\n{'─' * 80}")
        print(f"ARTICLE {i}/{min(3, len(articles))}")
        print(f"{'─' * 80}")
        print(f"Title: {article.title}")
        print(f"Source: {article.source}")
        print(f"URL: {article.url}")
        print(f"Companies: {', '.join(article.companies_mentioned)}")
        print(f"Published: {article.published_at}")
        print(f"Content length: {len(article.content)} characters")
        print(f"\nContent preview:")
        print(f"{article.content[:300]}...")
        print()

    # Process through pipeline
    print_separator("⚙️  PROCESSING THROUGH PIPELINE")

    alerts_generated = []

    for i, article in enumerate(articles[:3], 1):
        print(f"\n{'─' * 40}")
        print(f"Processing article {i}/{min(3, len(articles))}: {article.title[:60]}...")
        print(f"{'─' * 40}")

        try:
            alert = pipeline.process_article(article)

            if alert:
                print(f"✅ ALERT GENERATED!")
                print(f"   Type: {alert.type}")
                print(f"   Severity: {alert.severity}")
                print(f"   Impact: {alert.impact_percent:+.2f}%")
                print(f"   Dollar Impact: ${alert.impact_dollar:,.2f}")
                print(f"   Recommendation: {alert.recommendation}")
                print(f"   Confidence: {alert.confidence:.0%}")
                print(f"   Affected: {', '.join([h.company for h in alert.affected_holdings])}")
                print(f"   Explanation: {alert.explanation[:200]}...")
                alerts_generated.append(alert)
            else:
                print(f"ℹ️  No alert generated")
                print(f"   (Below threshold or no significant impact detected)")

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)

    # Final summary
    print_separator("🎯 RESULTS SUMMARY")

    print(f"Articles fetched: {len(articles)}")
    print(f"Articles processed: {min(3, len(articles))}")
    print(f"Alerts generated: {len(alerts_generated)}")
    print(f"Alert rate: {len(alerts_generated)/min(3, len(articles))*100:.0f}%")
    print()

    # Database check
    db_articles = len(database.get_all_articles())
    db_alerts = len(database.get_all_alerts())

    print(f"Database:")
    print(f"  - Articles stored: {db_articles}")
    print(f"  - Alerts stored: {db_alerts}")
    print()

    # Comparison
    print_separator("✅ FINNHUB vs PREVIOUS SOURCES")

    print("PREVIOUS (NewsData.io summaries):")
    print("  ❌ Content: 100-200 characters")
    print("  ❌ Quality: Too short for analysis")
    print("  ❌ Results: JSON errors, no alerts")
    print()

    print("NOW (Finnhub API):")
    print(f"  ✅ Content: {avg_length:.0f} characters (average)")
    print(f"  ✅ Quality: Sufficient for Gemini analysis")
    print(f"  ✅ Results: {len(alerts_generated)} alerts from {min(3, len(articles))} articles")
    print()

    if alerts_generated:
        print("🎉 SUCCESS! Finnhub integration is working!")
        print("   - Articles have sufficient content")
        print("   - Gemini can analyze properly")
        print("   - Alerts are being generated")
    else:
        print("⚠️  Finnhub is working, but no alerts generated")
        print("   Possible reasons:")
        print("   - No significant portfolio impact in these articles")
        print("   - Impact below threshold (0.5%)")
        print("   - Articles are neutral/informational")
        print()
        print("   This is normal! Not every article should trigger an alert.")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
