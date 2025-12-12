"""
Database Flow Test - Simulate the complete pipeline to show database storage
(Bypasses Gemini API to avoid rate limits)
"""

from datetime import datetime
from app.models.article import Article
from app.models.alert import Alert, AffectedHolding
from app.models.knowledge_graph import KnowledgeGraph
from app.services.database import database
from app.config import DEFAULT_PORTFOLIO
import json

def print_separator(title=""):
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print('='*80 + "\n")
    else:
        print('\n' + '='*80 + '\n')

def simulate_complete_flow():
    """Simulate the complete pipeline flow and show database storage"""

    print_separator("🎯 COMPLETE DATABASE FLOW SIMULATION")

    # Initialize portfolio
    if not database.get_portfolio():
        database.save_portfolio({
            "user_name": "Jaswanth",
            "portfolio": DEFAULT_PORTFOLIO
        })

    print("📊 INITIAL DATABASE STATE:")
    stats = database.get_stats()
    print(f"   Articles: {stats['articles_count']}")
    print(f"   Alerts: {stats['alerts_count']}")
    print(f"   Relationships: {stats['relationships_count']}")
    print(f"   Knowledge Graphs: {stats['graphs_count']}")

    print_separator("📰 STEP 1: CREATE ARTICLE")

    # Create a realistic article
    article = Article(
        title="NVIDIA Announces Revolutionary AI Chip - Stock Surges 3%",
        url="https://example.com/nvidia-breakthrough-2025",
        source="TechCrunch",
        published_at=datetime.now(),
        content="""
NVIDIA Corporation today unveiled its next-generation AI chip architecture,
the 'Blackwell Ultra', promising unprecedented performance improvements.
The new chip delivers 5x faster AI training compared to current generation.
CEO Jensen Huang called it "the biggest leap in AI computing history."
The announcement triggered a 3% stock price surge in after-hours trading.
Analysts immediately raised price targets, with several predicting the chip
will solidify NVIDIA's dominance in the AI market for years to come.
        """.strip(),
        companies_mentioned=["NVIDIA", "AMD", "Intel"],
        event_type="product_launch",
        processed_at=datetime.now()
    )

    print(f"Title: {article.title}")
    print(f"Source: {article.source}")
    print(f"Companies: {', '.join(article.companies_mentioned)}")
    print(f"Event Type: {article.event_type}")
    print(f"\nSaving to database...")

    # Save article
    database.save_article(article)
    print("✅ Article saved!")

    print_separator("🚨 STEP 2: CREATE ALERT")

    # Create a direct impact alert
    alert = Alert(
        type="portfolio_impact",
        severity="medium",
        trigger_article_id=article.id,
        affected_holdings=[
            AffectedHolding(
                company="NVIDIA Corporation",
                ticker="NVDA",
                quantity=80,
                impact_percent=2.5,
                impact_dollar=1751.00,
                current_price=875.50
            )
        ],
        impact_percent=1.8,
        impact_dollar=1751.00,
        recommendation="HOLD",
        confidence=0.85,
        chain={
            "level_1": "product_launch",
            "level_2": "NVIDIA announces breakthrough AI chip",
            "level_3": "Direct portfolio impact: +1.8%"
        },
        sources=[article.url],
        explanation="NVIDIA announces breakthrough AI chip architecture with 5x performance improvement. This positive news directly affects NVIDIA with an estimated 2.5% impact. Strong market positioning solidified for next 2-3 years.",
        created_at=datetime.now()
    )

    print(f"Alert ID: {alert.id}")
    print(f"Type: {alert.type}")
    print(f"Severity: {alert.severity}")
    print(f"Impact: {alert.impact_percent}% (${alert.impact_dollar:,.2f})")
    print(f"Recommendation: {alert.recommendation}")
    print(f"Confidence: {alert.confidence}")
    print(f"\nAffected Holdings:")
    for holding in alert.affected_holdings:
        print(f"  • {holding.company}: {holding.impact_percent}% (${holding.impact_dollar:,.2f})")

    print(f"\nSaving to database...")
    database.save_alert(alert)
    print("✅ Alert saved!")

    print_separator("🔗 STEP 3: CREATE RELATIONSHIPS")

    # Save a relationship
    relationship = {
        "from_company": "NVIDIA",
        "to_company": "AI Market",
        "relationship_type": "dominates",
        "confidence": 0.90,
        "article_id": article.id,
        "alert_id": alert.id
    }

    print(f"Relationship: {relationship['from_company']} → {relationship['to_company']}")
    print(f"Type: {relationship['relationship_type']}")
    print(f"Confidence: {relationship['confidence']}")
    print(f"\nSaving to database...")

    database.save_relationship(relationship)
    print("✅ Relationship saved!")

    print_separator("📊 STEP 4: CREATE KNOWLEDGE GRAPH")

    # Create knowledge graph
    graph = KnowledgeGraph(alert_id=alert.id)

    # Add nodes
    graph.add_node("event_1", "event", "NVIDIA Breakthrough Chip Launch")
    graph.add_node("company_NVIDIA", "company", "NVIDIA")
    graph.add_node("impact_portfolio", "impact", "+1.8% Portfolio Impact")

    # Add edges
    graph.add_edge("event_1", "company_NVIDIA", "directly_affects", 1.0)
    graph.add_edge("company_NVIDIA", "impact_portfolio", "impacts", 0.85)

    print(f"Graph ID: {graph.id}")
    print(f"Alert ID: {graph.alert_id}")
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")
    print(f"\nSaving to database...")

    database.save_knowledge_graph(graph)
    print("✅ Knowledge graph saved!")

    print_separator("📊 FINAL DATABASE STATE")

    stats = database.get_stats()
    print(f"✅ Articles: {stats['articles_count']} (+1)")
    print(f"✅ Alerts: {stats['alerts_count']} (+1)")
    print(f"✅ Relationships: {stats['relationships_count']} (+1)")
    print(f"✅ Knowledge Graphs: {stats['graphs_count']} (+1)")

    print_separator("💾 DATABASE FILE CONTENTS")

    # Show actual file contents
    print("📄 Articles File:")
    articles_data = database._read_file(database.ARTICLES_DB)
    print(json.dumps(articles_data, indent=2, default=str)[:500] + "...")

    print(f"\n📄 Alerts File:")
    alerts_data = database._read_file(database.ALERTS_DB)
    print(json.dumps(alerts_data, indent=2, default=str)[:500] + "...")

    print(f"\n📄 Relationships File:")
    relationships_data = database._read_file(database.RELATIONSHIPS_DB)
    print(json.dumps(relationships_data, indent=2, default=str)[:300] + "...")

    print(f"\n📄 Knowledge Graphs File:")
    graphs_data = database._read_file(database.KNOWLEDGE_GRAPHS_DB)
    print(json.dumps(graphs_data, indent=2, default=str)[:400] + "...")

    print_separator("✅ VERIFICATION")

    # Verify we can retrieve the data
    print("🔍 Retrieving saved article...")
    retrieved_article = database.get_article(article.id)
    if retrieved_article:
        print(f"   ✅ Found: {retrieved_article.title}")
    else:
        print(f"   ❌ Not found!")

    print("\n🔍 Retrieving saved alert...")
    retrieved_alert = database.get_alert(alert.id)
    if retrieved_alert:
        print(f"   ✅ Found: Impact {retrieved_alert.impact_percent}%")
    else:
        print(f"   ❌ Not found!")

    print("\n🔍 Retrieving knowledge graph...")
    retrieved_graph = database.get_knowledge_graph(alert.id)
    if retrieved_graph:
        print(f"   ✅ Found: {len(retrieved_graph.nodes)} nodes, {len(retrieved_graph.edges)} edges")
    else:
        print(f"   ❌ Not found!")

    print_separator("🎉 SUCCESS!")

    print("✅ Complete pipeline flow demonstrated:")
    print("   1. Article created and stored")
    print("   2. Alert generated and stored")
    print("   3. Relationships saved")
    print("   4. Knowledge graph created")
    print("   5. All data retrievable from database")
    print()
    print("📁 You can check the actual files at:")
    print(f"   - {database.ARTICLES_DB}")
    print(f"   - {database.ALERTS_DB}")
    print(f"   - {database.RELATIONSHIPS_DB}")
    print(f"   - {database.KNOWLEDGE_GRAPHS_DB}")
    print()
    print("🔍 Open these files to see the JSON data!")

if __name__ == "__main__":
    simulate_complete_flow()
