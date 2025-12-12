"""
Live News Test - Fetch real news, process through pipeline, check database
"""

import json
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database
from app.config import DEFAULT_PORTFOLIO

def print_separator(title=""):
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print('='*80 + "\n")
    else:
        print('\n' + '='*80 + '\n')

def print_database_contents():
    """Show what's in the database"""
    print_separator("💾 DATABASE CONTENTS")

    # Articles
    articles = database._read_file(database.ARTICLES_DB)
    print(f"📰 ARTICLES: {len(articles)}")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article.get('title', 'No title')[:80]}")
        print(f"   ID: {article.get('id')}")
        print(f"   Source: {article.get('source')}")
        print(f"   Companies: {', '.join(article.get('companies_mentioned', []))}")
        print(f"   URL: {article.get('url')[:60]}...")

    # Alerts
    alerts = database._read_file(database.ALERTS_DB)
    print(f"\n\n🚨 ALERTS: {len(alerts)}")
    for i, alert in enumerate(alerts, 1):
        print(f"\n{i}. Alert ID: {alert.get('id')}")
        print(f"   Type: {alert.get('type')}")
        print(f"   Severity: {alert.get('severity')}")
        print(f"   Impact: {alert.get('impact_percent')}% (${alert.get('impact_dollar')})")
        print(f"   Recommendation: {alert.get('recommendation')}")
        print(f"   Affected Holdings:")
        for holding in alert.get('affected_holdings', []):
            print(f"     • {holding.get('company')}: {holding.get('impact_percent')}%")
        print(f"   Explanation: {alert.get('explanation')[:150]}...")

    # Relationships
    relationships = database._read_file(database.RELATIONSHIPS_DB)
    print(f"\n\n🔗 RELATIONSHIPS: {len(relationships)}")
    for i, rel in enumerate(relationships, 1):
        print(f"\n{i}. {rel.get('from_company')} → {rel.get('to_company')}")
        print(f"   Type: {rel.get('relationship_type')}")
        print(f"   Confidence: {rel.get('confidence')}")

    # Knowledge Graphs
    graphs = database._read_file(database.KNOWLEDGE_GRAPHS_DB)
    print(f"\n\n📊 KNOWLEDGE GRAPHS: {len(graphs)}")
    for i, graph in enumerate(graphs, 1):
        print(f"\n{i}. Graph ID: {graph.get('id')}")
        print(f"   Alert ID: {graph.get('alert_id')}")
        print(f"   Nodes: {len(graph.get('nodes', []))}")
        print(f"   Edges: {len(graph.get('edges', []))}")

def main():
    print_separator("🧪 LIVE NEWS TEST WITH DATABASE VERIFICATION")

    # Initialize portfolio
    if not database.get_portfolio():
        database.save_portfolio({
            "user_name": "Jaswanth",
            "portfolio": DEFAULT_PORTFOLIO
        })
        print("✓ Portfolio initialized")

    # Show initial database state
    stats = database.get_stats()
    print("\n📊 INITIAL DATABASE STATE:")
    print(f"   Articles: {stats['articles_count']}")
    print(f"   Alerts: {stats['alerts_count']}")
    print(f"   Relationships: {stats['relationships_count']}")
    print(f"   Knowledge Graphs: {stats['graphs_count']}")

    print_separator("📰 STEP 1: FETCHING LIVE NEWS")

    # Fetch news
    print("Fetching from news sources...")
    articles = news_aggregator.fetch_all()

    print(f"\n✅ Fetched {len(articles)} articles")

    if not articles:
        print("\n⚠️ No articles found. Exiting.")
        return

    # Show articles
    print("\n📋 ARTICLES RETRIEVED:")
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. {article.title}")
        print(f"   Source: {article.source}")
        print(f"   Companies: {', '.join(article.companies_mentioned)}")

    print_separator("🔄 STEP 2: PROCESSING THROUGH PIPELINE")

    # Process articles
    alerts_generated = []
    for i, article in enumerate(articles[:3], 1):
        print(f"\n[{i}/{min(3, len(articles))}] Processing: {article.title[:60]}...")

        try:
            alert = pipeline.process_article(article)

            if alert:
                alerts_generated.append(alert)
                print(f"   ✅ Alert generated!")
                print(f"      Impact: {alert.impact_percent}%")
                print(f"      Severity: {alert.severity}")
            else:
                print(f"   ℹ️  No alert generated")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    print_separator("📊 STEP 3: RESULTS SUMMARY")

    print(f"Articles Processed: {min(3, len(articles))}")
    print(f"Alerts Generated: {len(alerts_generated)}")

    # Show final database state
    stats = database.get_stats()
    print("\n📊 FINAL DATABASE STATE:")
    print(f"   Articles: {stats['articles_count']} (new)")
    print(f"   Alerts: {stats['alerts_count']} (new)")
    print(f"   Relationships: {stats['relationships_count']} (new)")
    print(f"   Knowledge Graphs: {stats['graphs_count']} (new)")

    # Show detailed database contents
    if stats['articles_count'] > 0 or stats['alerts_count'] > 0:
        print_database_contents()

    print_separator("✅ TEST COMPLETE")

    if alerts_generated:
        print("\n🎉 SUCCESS! Alerts were generated and stored in database!")
        print("\nYou can verify by checking these files:")
        print(f"   - {database.ARTICLES_DB}")
        print(f"   - {database.ALERTS_DB}")
        print(f"   - {database.KNOWLEDGE_GRAPHS_DB}")
    else:
        print("\nℹ️  No alerts generated. Possible reasons:")
        print("   - Impact too small (< 0.5% threshold)")
        print("   - No direct impact detected")
        print("   - Gemini API rate limit")
        print("   - Article content insufficient")

if __name__ == "__main__":
    print("\n⏰ Waiting 10 seconds for Gemini API rate limit...")
    import time
    time.sleep(10)
    print("✅ Starting test...\n")

    main()
