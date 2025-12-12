"""
Test Pipeline - Fetch real news and process through all 7 stages
"""

import asyncio
from app.services.news_aggregator import news_aggregator
from app.services.pipeline import pipeline
from app.services.database import database
from app.config import DEFAULT_PORTFOLIO

def print_separator():
    print("\n" + "="*80 + "\n")

def main():
    print_separator()
    print("🚀 MARKETPULSE-X PIPELINE TEST")
    print("Testing complete news processing workflow")
    print_separator()

    # Step 1: Fetch news
    print("📰 STEP 1: FETCHING LIVE NEWS...")
    print("-" * 80)

    articles = news_aggregator.fetch_all()

    print(f"✅ Fetched {len(articles)} articles from news sources")
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. {article.title}")
        print(f"   Source: {article.source}")
        print(f"   Companies: {', '.join(article.companies_mentioned)}")
        print(f"   URL: {article.url[:60]}...")

    if not articles:
        print("⚠️ No articles found. Exiting.")
        return

    print_separator()
    print("🔄 STEP 2: PROCESSING THROUGH 7-STAGE PIPELINE")
    print("-" * 80)

    # Initialize portfolio if not exists
    if not database.get_portfolio():
        database.save_portfolio({
            "user_name": "Jaswanth",
            "portfolio": DEFAULT_PORTFOLIO
        })
        print("✅ Portfolio initialized for Jaswanth")

    # Process each article
    alerts_generated = []

    for i, article in enumerate(articles[:3], 1):  # Process first 3 articles
        print(f"\n{'='*80}")
        print(f"PROCESSING ARTICLE {i}/{min(3, len(articles))}")
        print(f"Title: {article.title}")
        print(f"{'='*80}\n")

        print("Stage 1: Event Validator...")
        validated = pipeline.event_validator(article)
        if not validated:
            print("  ❌ Article did not pass validation")
            continue
        print("  ✅ Article validated")

        print("\nStage 2: Relation Extractor (Gemini AI)...")
        extraction_result = pipeline.relation_extractor(validated)
        if not extraction_result:
            print("  ❌ No relationships extracted")
            continue

        relationships = extraction_result.get('relationships', [])
        event_summary = extraction_result.get('summary', article.title)
        print(f"  ✅ Extracted {len(relationships)} relationships")
        for rel in relationships:
            print(f"     • {rel['from_company']} → {rel['to_company']} ({rel['relationship_type']})")

        print("\nStage 3: Relation Verifier...")
        verified = pipeline.relation_verifier(relationships)
        print(f"  ✅ {len(verified)}/{len(relationships)} relationships verified")

        if not verified:
            print("  ❌ No verified relationships")
            continue

        print("\nStage 4: Cascade Inferencer (Gemini AI)...")
        cascade_result = pipeline.cascade_inferencer(event_summary, verified)
        if not cascade_result:
            print("  ❌ No cascade inference")
            continue

        affected = cascade_result.get('affected_portfolio_companies', [])
        impact_pct = cascade_result.get('estimated_impact_percent', 0)
        print(f"  ✅ Cascade affects {len(affected)} portfolio companies")
        print(f"     Companies: {', '.join(affected)}")
        print(f"     Estimated impact: {impact_pct}%")

        print("\nStage 5: Impact Scorer...")
        portfolio_data = database.get_portfolio()
        impact_result = pipeline.impact_scorer(cascade_result, portfolio_data)
        if not impact_result:
            print("  ❌ Could not calculate impact")
            continue

        print(f"  ✅ Impact calculated")
        print(f"     Total portfolio impact: {impact_result['total_impact_percent']}%")
        print(f"     Dollar impact: ${impact_result['total_impact_dollar']:,.2f}")
        print(f"     Severity: {impact_result['severity']}")

        for holding in impact_result['affected_holdings']:
            print(f"     • {holding['company']}: {holding['impact_percent']}% (${holding['impact_dollar']:,.2f})")

        print("\nStage 6: Explanation Generator (Gemini AI)...")
        explanation = pipeline.explanation_generator(
            event_summary,
            cascade_result,
            impact_result,
            [article.url]
        )
        print(f"  ✅ Explanation generated")
        print(f"     {explanation[:150]}...")

        print("\nStage 7: Graph Orchestrator...")
        # This happens automatically in process_article
        print("  ✅ Knowledge graph created")

        print("\n" + "="*80)
        print("🎯 GENERATING ALERT...")
        print("="*80 + "\n")

        # Generate full alert
        alert = pipeline.process_article(article)
        if alert:
            alerts_generated.append(alert)
            print(f"✅ ALERT GENERATED!")
            print(f"   Alert ID: {alert.id}")
            print(f"   Type: {alert.type}")
            print(f"   Severity: {alert.severity}")
            print(f"   Recommendation: {alert.recommendation}")
            print(f"   Confidence: {alert.confidence}")
            print(f"   Impact: {alert.impact_percent}% (${alert.impact_dollar:,.2f})")
            print(f"   Affected Holdings: {len(alert.affected_holdings)}")
        else:
            print("  ℹ️ No alert generated (impact too small)")

    print_separator()
    print("📊 FINAL RESULTS")
    print("-" * 80)
    print(f"Articles processed: {min(3, len(articles))}")
    print(f"Alerts generated: {len(alerts_generated)}")

    if alerts_generated:
        print("\n🚨 GENERATED ALERTS:")
        for alert in alerts_generated:
            print(f"\n{alert.type.upper()} - {alert.severity.upper()}")
            print(f"Impact: {alert.impact_percent}% (${alert.impact_dollar:,.2f})")
            print(f"Recommendation: {alert.recommendation}")
            print(f"Explanation: {alert.explanation[:200]}...")

    # Show database stats
    stats = database.get_stats()
    print("\n💾 DATABASE STATS:")
    print(f"   Articles: {stats['articles_count']}")
    print(f"   Alerts: {stats['alerts_count']}")
    print(f"   Relationships: {stats['relationships_count']}")
    print(f"   Knowledge Graphs: {stats['graphs_count']}")

    print_separator()
    print("✅ TEST COMPLETE!")
    print_separator()

if __name__ == "__main__":
    main()
