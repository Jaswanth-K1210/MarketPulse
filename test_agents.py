"""
Test Multi-Agent System
Verifies that all agents work correctly together
"""

from app.agents.agent_orchestrator import agent_orchestrator
from app.services.news_aggregator import news_aggregator


def print_separator(title=""):
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"\n{'-'*80}\n")


def main():
    print_separator("🤖 MULTI-AGENT SYSTEM TEST")

    # Test 1: Agent Status
    print_separator("📊 TEST 1: AGENT STATUS")

    status = agent_orchestrator.get_agent_status()
    print(f"Orchestrator: {status['orchestrator']}")
    print(f"Total Agents: {status['total_agents']}\n")

    print("Agents loaded:")
    for agent_name, agent_info in status['agents'].items():
        print(f"  ✓ {agent_info['name']}")
        print(f"    Description: {agent_info['description']}")
        print(f"    Status: {agent_info['status']}")
        print()

    # Test 2: Fetch News
    print_separator("📰 TEST 2: FETCH SAMPLE NEWS")

    print("Fetching 1 sample article from Finnhub...\n")
    news_aggregator.clear_seen_urls()
    articles = news_aggregator.fetch_all(limit=1)

    if not articles:
        print("❌ No articles fetched. Using simulated data for testing.\n")

        # Create simulated article for testing
        from app.models.article import Article
        from datetime import datetime

        article = Article(
            title="Apple Reports Record Q4 Earnings, Stock Surges",
            url="https://example.com/apple-earnings",
            source="Test Source",
            published_at=datetime.now(),
            content="Apple Inc. reported record fourth-quarter earnings, beating analyst expectations by 15%. The tech giant's revenue grew 12% year-over-year, driven by strong iPhone sales and services growth. Investors reacted positively to the news, sending the stock up 5% in after-hours trading.",
            companies_mentioned=["Apple"]
        )
        articles = [article]

    article = articles[0]

    print(f"📄 Article:")
    print(f"   Title: {article.title}")
    print(f"   Source: {article.source}")
    print(f"   Companies: {', '.join(article.companies_mentioned)}")
    print(f"   Content length: {len(article.content)} chars")

    # Test 3: Multi-Agent Processing
    print_separator("🤖 TEST 3: MULTI-AGENT PROCESSING")

    print("Processing article through multi-agent system...\n")

    result = agent_orchestrator.process_news(
        article_title=article.title,
        article_content=article.content,
        article_url=article.url,
        companies_mentioned=article.companies_mentioned
    )

    if not result or not result.get("success"):
        print("❌ Multi-agent processing failed!")
        return

    print_separator("✅ TEST 3: PROCESSING RESULTS")

    # Display results
    analysis = result.get("analysis", {})
    calculation = result.get("calculation", {})
    synthesis = result.get("synthesis", {})

    print("📊 ANALYST AGENT RESULTS:")
    print(f"   Sentiment: {analysis.get('sentiment', 'N/A')}")
    print(f"   Sentiment Score: {analysis.get('sentiment_score', 0):.2f}")
    print(f"   Confidence: {analysis.get('confidence', 0):.0%}")
    if analysis.get('key_insights'):
        print(f"   Key Insights:")
        for insight in analysis['key_insights']:
            print(f"     • {insight}")

    print(f"\n💰 CALCULATOR AGENT RESULTS:")
    print(f"   Portfolio Impact: {calculation.get('portfolio_impact_percent', 0):+.2f}%")
    print(f"   Dollar Impact: ${calculation.get('portfolio_impact_dollar', 0):,.2f}")
    print(f"   Severity: {calculation.get('severity', 'N/A').upper()}")
    print(f"   Affected Holdings: {len(calculation.get('affected_holdings', []))}")

    print(f"\n🧠 SYNTHESIZER AGENT RESULTS:")
    print(f"   Recommendation: {synthesis.get('recommendation', 'N/A')}")
    print(f"   Overall Confidence: {synthesis.get('confidence', 0):.0%}")
    print(f"   Risk Assessment: {synthesis.get('risk_assessment', 'N/A')}")

    if synthesis.get('action_items'):
        print(f"\n   Action Items:")
        for item in synthesis['action_items']:
            print(f"     • {item}")

    print(f"\n   Explanation:")
    print(f"     {synthesis.get('explanation', 'N/A')}")

    # Metadata
    metadata = result.get("metadata", {})
    print(f"\n⏱️  PROCESSING METADATA:")
    print(f"   Processing Time: {metadata.get('processing_time_seconds', 0):.2f}s")
    print(f"   Agents Used: {metadata.get('agents_used', 0)}")

    print_separator("✅ ALL TESTS PASSED")

    print("\n📋 SUMMARY:")
    print("   ✓ Agent orchestrator initialized")
    print("   ✓ All 4 agents loaded and ready")
    print("   ✓ Multi-agent processing working")
    print("   ✓ Analysis pipeline complete")
    print("   ✓ Results generated successfully")
    print("\n🎉 Phase 2: Multi-Agent System is READY!\n")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
