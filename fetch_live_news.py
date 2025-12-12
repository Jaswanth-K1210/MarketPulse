"""
Fetch Live News and Generate Alerts
Shows news in the same format as the 9:10 test
"""

import asyncio
from datetime import datetime
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database

def print_separator(char="=", length=80):
    print(f"\n{char * length}")

async def main():
    print_separator()
    print("  🚀 FETCHING LIVE NEWS FROM FINNHUB")
    print_separator()
    print()

    # Clear cache for fresh fetch
    news_aggregator.clear_seen_urls()

    # Fetch live articles
    print("📰 Fetching latest news for portfolio companies...")
    print("   Companies: AAPL, NVDA, AMD, INTC, AVGO")
    print()

    articles = news_aggregator.fetch_from_finnhub()

    if not articles:
        print("❌ No articles fetched")
        return

    print(f"✅ Fetched {len(articles)} live articles\n")

    print_separator()
    print("  📄 NEWS ARTICLES")
    print_separator()

    # Show articles in the requested format
    for i, article in enumerate(articles[:10], 1):
        print(f"\n{'─' * 80}")
        print(f"📰 ARTICLE {i}/{min(10, len(articles))}")
        print(f"{'─' * 80}")
        print(f"Title:      {article.title}")
        print(f"Source:     {article.source}")
        print(f"URL:        {article.url}")
        print(f"Published:  {article.published_at}")
        print(f"Companies:  {', '.join(article.companies_mentioned)}")
        print(f"Content:    {article.content[:200]}...")
        print(f"Length:     {len(article.content)} characters")

    print_separator()
    print("  ⚙️  PROCESSING THROUGH PIPELINE")
    print_separator()

    alerts_generated = []

    # Process each article
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] Processing: {article.title[:60]}...")

        try:
            alert = pipeline.process_article(article)

            if alert:
                print(f"    ✅ ALERT GENERATED!")
                print(f"       Impact: {alert.impact_percent:+.2f}%")
                print(f"       Severity: {alert.severity}")
                print(f"       Recommendation: {alert.recommendation}")
                alerts_generated.append(alert)
            else:
                print(f"    ℹ️  No alert (below threshold)")

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")

    print_separator()
    print("  🚨 ALERTS GENERATED")
    print_separator()

    if alerts_generated:
        print(f"\n✅ Generated {len(alerts_generated)} new alerts!\n")

        for i, alert in enumerate(alerts_generated, 1):
            print(f"\n{'─' * 80}")
            print(f"🚨 ALERT {i}/{len(alerts_generated)}")
            print(f"{'─' * 80}")
            print(f"ID:              {alert.id}")
            print(f"Type:            {alert.type}")
            print(f"Severity:        {alert.severity}")
            print(f"Portfolio Impact: {alert.impact_percent:+.2f}% (${alert.impact_dollar:,.2f})")
            print(f"Recommendation:  {alert.recommendation}")
            print(f"Confidence:      {alert.confidence:.0%}")
            print(f"\nAffected Holdings:")
            for holding in alert.affected_holdings:
                print(f"  • {holding.company} ({holding.ticker})")
                print(f"    {holding.quantity} shares @ ${holding.current_price:.2f}")
                print(f"    Impact: {holding.impact_percent:+.1f}% = ${holding.impact_dollar:,.2f}")
            print(f"\nExplanation:")
            print(f"  {alert.explanation}")
            print(f"\nSources:")
            for source in alert.sources:
                print(f"  - {source}")
    else:
        print("\nℹ️  No alerts generated")
        print("   This is normal - not every article triggers an alert")

    print_separator()
    print("  💾 DATABASE STATUS")
    print_separator()

    db_articles = database.get_all_articles()
    db_alerts = database.get_all_alerts()

    print(f"\n📊 Total in Database:")
    print(f"   Articles: {len(db_articles)}")
    print(f"   Alerts:   {len(db_alerts)}")

    if len(db_alerts) > 0:
        print(f"\n📈 Latest 3 Alerts:")
        for i, alert in enumerate(list(db_alerts)[-3:], 1):
            print(f"   {i}. {alert.severity.upper()}: {alert.impact_percent:+.2f}% impact")
            print(f"      Affects: {', '.join([h.company for h in alert.affected_holdings])}")

    print_separator()
    print("  ✅ SUMMARY")
    print_separator()

    print(f"""
📰 Articles Fetched:    {len(articles)}
⚙️  Articles Processed:  {len(articles)}
🚨 Alerts Generated:    {len(alerts_generated)}
💾 Saved to Database:   ✅

Alert Rate: {len(alerts_generated)/len(articles)*100:.1f}%
""")

    print_separator()
    print()


if __name__ == "__main__":
    asyncio.run(main())
