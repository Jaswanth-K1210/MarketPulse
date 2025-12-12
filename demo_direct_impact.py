"""
Demo: Direct Impact Detection
Shows how the new feature works with a realistic article
"""

from datetime import datetime
from app.models.article import Article
from app.services.pipeline import pipeline
from app.services.database import database
from app.config import DEFAULT_PORTFOLIO

def print_separator(char="="):
    print("\n" + char*80 + "\n")

def main():
    print_separator()
    print("🎯 DIRECT IMPACT DETECTION DEMO")
    print("Demonstrating the new pipeline feature")
    print_separator()

    # Initialize portfolio
    if not database.get_portfolio():
        database.save_portfolio({
            "user_name": "Jaswanth",
            "portfolio": DEFAULT_PORTFOLIO
        })

    # Create realistic test article about NVIDIA
    test_article = Article(
        title="NVIDIA Announces Breakthrough AI Chip - Stock Surges 3%",
        url="https://example.com/nvidia-ai-chip-2025",
        source="TechNews",
        published_at=datetime.now(),
        content="""
NVIDIA Corporation announced today a groundbreaking new AI chip architecture
that promises 5x performance improvements over current generation chips.
The new "Blackwell Ultra" chip features advanced tensor cores and is
specifically designed for large language model training and inference.

CEO Jensen Huang stated: "This represents the biggest leap in AI computing
power we've ever achieved. We expect massive demand from cloud providers
and enterprise customers."

Market analysts immediately upgraded NVIDIA's stock price targets, with
Morgan Stanley raising its target from $800 to $950 per share. The stock
surged 3% in after-hours trading on the announcement.

Industry experts believe this positions NVIDIA ahead of competitors AMD
and Intel in the AI chip race for the next 2-3 years. Pre-orders from
major cloud providers including Microsoft, Google, and Amazon have already
exceeded production capacity for Q1 2025.

NVIDIA's data center revenue is expected to grow 40% year-over-year as
a result of this product launch. The company plans to begin shipping
the new chips in February 2025.
        """.strip(),
        companies_mentioned=["NVIDIA", "AMD", "Intel"]
    )

    print("📰 TEST ARTICLE:")
    print("-" * 80)
    print(f"Title: {test_article.title}")
    print(f"Source: {test_article.source}")
    print(f"Companies Mentioned: {', '.join(test_article.companies_mentioned)}")
    print(f"\nContent Preview:")
    print(test_article.content[:300] + "...")

    print_separator()
    print("🔄 PROCESSING THROUGH PIPELINE...")
    print("-" * 80)

    # Process article
    alert = pipeline.process_article(test_article)

    print_separator()

    if alert:
        print("✅ SUCCESS! ALERT GENERATED WITH DIRECT IMPACT DETECTION")
        print_separator("=")

        print("📊 ALERT DETAILS:")
        print("-" * 80)
        print(f"Alert ID: {alert.id}")
        print(f"Type: {alert.type}")
        print(f"Severity: {alert.severity.upper()}")
        print(f"Confidence: {alert.confidence}")

        print(f"\n💰 PORTFOLIO IMPACT:")
        print("-" * 80)
        print(f"Total Impact: {alert.impact_percent:+.2f}%")
        print(f"Dollar Impact: ${alert.impact_dollar:+,.2f}")
        print(f"Recommendation: {alert.recommendation}")

        print(f"\n🏢 AFFECTED HOLDINGS:")
        print("-" * 80)
        for holding in alert.affected_holdings:
            print(f"  • {holding.company} ({holding.ticker})")
            print(f"    - Quantity: {holding.quantity} shares")
            print(f"    - Impact: {holding.impact_percent:+.2f}% (${holding.impact_dollar:+,.2f})")

        print(f"\n📝 EXPLANATION:")
        print("-" * 80)
        print(f"{alert.explanation}")

        print(f"\n🔗 IMPACT CHAIN:")
        print("-" * 80)
        for level, desc in alert.chain.items():
            print(f"  {level}: {desc}")

        print(f"\n📚 SOURCES:")
        print("-" * 80)
        for source in alert.sources:
            print(f"  • {source}")

        print_separator()
        print("✅ DEMO COMPLETE - Direct Impact Detection Working!")
        print_separator()

        # Show database stats
        stats = database.get_stats()
        print("\n💾 DATABASE UPDATED:")
        print(f"   Articles: {stats['articles_count']}")
        print(f"   Alerts: {stats['alerts_count']}")
        print(f"   Knowledge Graphs: {stats['graphs_count']}")

    else:
        print("❌ No alert generated")
        print("   This might happen if:")
        print("   - Impact too small (< 0.5%)")
        print("   - Gemini API rate limit hit")
        print("   - No portfolio companies affected")

    print_separator()

if __name__ == "__main__":
    print("\n⏰ Waiting 60 seconds for Gemini API rate limit to reset...")
    import time
    time.sleep(60)  # Wait for rate limit to reset
    print("✅ Proceeding with demo...\n")

    main()
