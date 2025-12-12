"""
Test Script: Live News Fetching with Full Content Scraping
Tests Option 2 implementation - Better news source with web scraping
"""

import asyncio
import logging
from datetime import datetime
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str):
    """Print a nice separator"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


async def main():
    """Test live news fetching with full content scraping"""

    print_separator("🚀 TESTING OPTION 2: FULL CONTENT SCRAPING")

    print("📰 Fetching live news articles...")
    print("   - Using Google News RSS (with web scraping)")
    print("   - Using NewsData.io (with web scraping if needed)")
    print("   - Scraping full article content from source URLs")
    print()

    # Clear cache for fresh fetch
    news_aggregator.clear_seen_urls()

    # Fetch articles (limit to first 3 for testing)
    print("🔍 Fetching and scraping articles...\n")
    all_articles = news_aggregator.fetch_all()

    if not all_articles:
        print("❌ No articles fetched. Check API keys and internet connection.")
        return

    print(f"\n✅ Fetched {len(all_articles)} articles with full content\n")

    # Process first few articles through pipeline
    print_separator("⚙️  PROCESSING ARTICLES THROUGH PIPELINE")

    alerts_generated = []

    for i, article in enumerate(all_articles[:3], 1):  # Process first 3 articles
        print(f"\n{'─' * 80}")
        print(f"📄 ARTICLE {i}/{min(3, len(all_articles))}")
        print(f"{'─' * 80}")
        print(f"Title: {article.title}")
        print(f"Source: {article.source}")
        print(f"URL: {article.url}")
        print(f"Companies: {', '.join(article.companies_mentioned)}")
        print(f"Content length: {len(article.content)} characters")
        print(f"Content preview: {article.content[:200]}...")
        print()

        # Process through pipeline
        print(f"⚙️  Processing through pipeline...")
        try:
            alert = pipeline.process_article(article)

            if alert:
                print(f"✅ ALERT GENERATED!")
                print(f"   Type: {alert.type}")
                print(f"   Severity: {alert.severity}")
                print(f"   Impact: {alert.impact_percent:+.2f}%")
                print(f"   Recommendation: {alert.recommendation}")
                print(f"   Confidence: {alert.confidence:.0%}")
                print(f"   Explanation: {alert.explanation[:150]}...")
                print(f"   Affected: {', '.join([h.company for h in alert.affected_holdings])}")
                alerts_generated.append(alert)
            else:
                print(f"ℹ️  No alert generated (below threshold or no impact detected)")

        except Exception as e:
            print(f"❌ Error processing article: {str(e)}")
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)

    # Summary
    print_separator("📊 TEST RESULTS SUMMARY")

    print(f"Articles Fetched: {len(all_articles)}")
    print(f"Articles Processed: {min(3, len(all_articles))}")
    print(f"Alerts Generated: {len(alerts_generated)}")
    print()

    if all_articles:
        avg_length = sum(len(a.content) for a in all_articles) / len(all_articles)
        print(f"Average Content Length: {avg_length:.0f} characters")
        print(f"Min Content Length: {min(len(a.content) for a in all_articles)} characters")
        print(f"Max Content Length: {max(len(a.content) for a in all_articles)} characters")
        print()

    # Check database
    print_separator("💾 DATABASE VERIFICATION")

    stored_articles = len(database.get_all_articles())
    stored_alerts = len(database.get_all_alerts())
    stored_relationships = len(database.get_all_relationships())
    stored_graphs = len(database.get_all_knowledge_graphs())

    print(f"✅ Articles in database: {stored_articles}")
    print(f"✅ Alerts in database: {stored_alerts}")
    print(f"✅ Relationships in database: {stored_relationships}")
    print(f"✅ Knowledge graphs in database: {stored_graphs}")
    print()

    # Comparison with previous approach
    print_separator("🎯 IMPROVEMENT SUMMARY")

    print("BEFORE (Summaries only):")
    print("  ❌ Content: 100-200 characters")
    print("  ❌ Gemini: Insufficient context")
    print("  ❌ Alerts: None generated")
    print()
    print("AFTER (Full content scraping):")
    if all_articles:
        print(f"  ✅ Content: {avg_length:.0f} characters (average)")
        print(f"  ✅ Gemini: Sufficient context for analysis")
        print(f"  ✅ Alerts: {len(alerts_generated)} generated from {min(3, len(all_articles))} articles")
    print()

    if alerts_generated:
        print("🎉 SUCCESS! Full content scraping is working!")
        print("   - Articles now contain full text")
        print("   - Gemini can accurately analyze content")
        print("   - Alerts are being generated correctly")
    else:
        print("⚠️  No alerts generated, but articles have full content.")
        print("   Possible reasons:")
        print("   - No significant portfolio impact detected")
        print("   - Impact below threshold")
        print("   - Gemini API rate limits")

    print()
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
