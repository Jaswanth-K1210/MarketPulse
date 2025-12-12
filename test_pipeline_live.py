"""
Live Pipeline Test - Same Format as 9:10 PM Test
Fetches real news with actual source URLs and processes through pipeline
"""

import asyncio
from datetime import datetime
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database


def print_header(text):
    print(f"\n{'='*80}")
    print(f"{text}")
    print(f"{'='*80}\n")


def print_section(text):
    print(f"\n{'-'*80}")
    print(f"{text}")
    print(f"{'-'*80}")


async def main():
    print_header("🚀 MARKETPULSE-X PIPELINE TEST")
    print("Testing complete news processing workflow\n")
    print("="*80)

    # Clear cache
    news_aggregator.clear_seen_urls()

    # STEP 1: Fetch News
    print_section("📰 STEP 1: FETCHING LIVE NEWS...")

    # Fetch from all available sources
    print("Fetching from all news sources...\n")

    # Use fetch_all() which tries all sources
    all_articles = news_aggregator.fetch_all()

    if not all_articles:
        print("❌ No articles fetched")
        return

    print(f"✅ Fetched {len(all_articles)} articles from news sources\n")

    # Display articles in the 9:10 format
    for i, article in enumerate(all_articles[:10], 1):
        print(f"{i}. {article.title}")
        print(f"   Source: {article.source}")
        print(f"   Companies: {', '.join(article.companies_mentioned)}")
        # Truncate URL for display
        url_display = article.url[:70] + "..." if len(article.url) > 70 else article.url
        print(f"   URL: {url_display}")
        print()

    # STEP 2: Process through pipeline
    print_section("⚙️  STEP 2: PROCESSING THROUGH PIPELINE...")

    alerts_generated = []
    processed_count = 0

    for i, article in enumerate(all_articles, 1):
        print(f"\n[{i}/{len(all_articles)}] Processing: {article.title[:60]}...")

        try:
            alert = pipeline.process_article(article)
            processed_count += 1

            if alert:
                print(f"    ✅ ALERT GENERATED!")
                print(f"       Severity: {alert.severity}")
                print(f"       Impact: {alert.impact_percent:+.2f}%")
                print(f"       Recommendation: {alert.recommendation}")
                alerts_generated.append(alert)
            else:
                print(f"    ℹ️  No alert (below threshold)")

        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            # Check if it's a rate limit error
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"    ⚠️  Gemini API rate limit reached")
                print(f"    📊 Processed {processed_count} articles before limit")
                break

    # STEP 3: Show generated alerts
    print_section("🚨 STEP 3: ALERTS GENERATED")

    if alerts_generated:
        print(f"\n✅ {len(alerts_generated)} alert(s) generated!\n")

        for i, alert in enumerate(alerts_generated, 1):
            print(f"\n{'─'*80}")
            print(f"ALERT #{i}")
            print(f"{'─'*80}")
            print(f"ID:              {alert.id}")
            print(f"Type:            {alert.type}")
            print(f"Severity:        {alert.severity.upper()}")
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
        print(f"\nℹ️  No alerts generated from processed articles")
        print(f"   Possible reasons:")
        print(f"   - Articles are informational/neutral")
        print(f"   - Impact below threshold (0.5%)")
        print(f"   - Gemini API rate limit reached")

    # STEP 4: Database Status
    print_section("💾 STEP 4: DATABASE STATUS")

    db_articles = database.get_all_articles()
    db_alerts = database.get_all_alerts()

    print(f"\n📊 Database Statistics:")
    print(f"   Articles: {len(db_articles)}")
    print(f"   Alerts:   {len(db_alerts)}")

    if db_alerts:
        print(f"\n📈 All Alerts in Database:")
        for i, alert in enumerate(db_alerts, 1):
            affected = ', '.join([h.company for h in alert.affected_holdings])
            print(f"   {i}. [{alert.severity.upper()}] {alert.impact_percent:+.2f}% - {affected}")

    # Summary
    print_section("✅ TEST SUMMARY")

    print(f"""
📰 Articles Fetched:     {len(all_articles)}
⚙️  Articles Processed:   {processed_count}
🚨 Alerts Generated:     {len(alerts_generated)}
💾 Total Alerts in DB:   {len(db_alerts)}

Alert Rate: {(len(alerts_generated)/processed_count*100) if processed_count > 0 else 0:.1f}%
""")

    print("="*80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
