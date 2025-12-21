
import asyncio
from datetime import datetime, timezone
from app.services.pipeline import Pipeline
from app.models.article import Article
from app.services.database import get_db_connection

async def test_pipeline():
    print("🚀 Starting Pipeline Smoke Test...")
    
    # Use naive time to match backend likely format
    pub_date = datetime.now()
    
    # 1. Create a "Known Good" High Impact Article
    article = Article(
        title="TSMC Halts 3nm Chip Production for Apple and NVIDIA",
        url="https://test.com/tsmc-halt",
        source="Bloomberg",
        published_at=pub_date,
        summary="TSMC has suspended 3nm chip manufacturing due to a critical material shortage from Japanese suppliers. This halts production for Apple's A17 Bionic and NVIDIA's H100 GPU lines effectively immediately. Delays are expected to last 4-6 weeks.",
        content="TSMC has suspended 3nm chip manufacturing due to a critical material shortage from Japanese suppliers. This halts production for Apple's A17 Bionic and NVIDIA's H100 GPU lines effectively immediately. Delays are expected to last 4-6 weeks."
    )
    
    pipeline = Pipeline()
    
    print(f"📰 Processing Article: {article.title}")
    # Sync call
    result = pipeline.process_article(article)
    
    if result:
        print("✅ Alert Generated!")
        print(f"Title: {result.headline}")
        print(f"Severity: {result.severity}")
        print(f"Impact: {result.impact_pct}%")
    else:
        print("❌ No Alert Generated (Check Logs)")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
