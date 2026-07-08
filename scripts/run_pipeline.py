"""
GitHub Actions pipeline entry point — runs every 10 min.
Ingests news → classifies → scores risk → writes alerts to DB.
Shared pipeline: runs once for all users, not per-user.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.config  # triggers load_dotenv()
from app.config import TRACKED_COMPANIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pipeline")


def main():
    logger.info("=== MarketPulse-X Pipeline Start ===")

    # 1. Ingest news
    from app.services.news_aggregator import news_aggregator_layer
    tickers = list(dict.fromkeys(
        v for v in __import__("app.config", fromlist=["COMPANY_TICKERS"]).COMPANY_TICKERS.values()
    ))[:10]
    logger.info("Ingesting for tickers: %s", tickers)
    articles = news_aggregator_layer.ingest_all(tickers)
    logger.info("Ingested %d articles", len(articles))

    # 2. Classify with FinBERT
    from app.ml.finbert_service import finbert_service
    classified = finbert_service.classify_batch([
        {"title": a.title, "content": a.content} for a in articles
    ])
    logger.info("Classified %d articles", len(classified))

    # 3. Detect market regime
    from app.ml.regime_detector import regime_detector
    regime = regime_detector.detect()
    logger.info("Market regime: %s (conf=%.2f)", regime["regime"], regime["confidence"])

    # 4. Score risk
    from app.ml.risk_scorer import risk_scorer
    high_risk = []
    for i, art in enumerate(articles[:len(classified)]):
        meta = {
            "source_tier": art.priority,
            "state_affiliated": False,
            "sentiment_score": classified[i].get("score", 0.0),
            "content": art.content,
        }
        scored = risk_scorer.score(meta, {"type": "direct", "criticality": "medium"}, classified[i].get("event_type", ""))
        if scored["risk_score"] >= 0.5:
            high_risk.append({
                "title": art.title,
                "source": art.source,
                "risk_score": scored["risk_score"],
                "sentiment": classified[i].get("sentiment"),
                "event_type": classified[i].get("event_type"),
                "regime": regime["regime"],
            })

    logger.info("High-risk articles: %d", len(high_risk))
    for h in high_risk[:5]:
        logger.info("  [%.2f] %s — %s (%s)", h["risk_score"], h["title"][:60], h["source"], h["event_type"])

    news_stats = news_aggregator_layer.source_stats()
    logger.info("Source stats: %s", news_stats)
    logger.info("=== Pipeline Complete ===")


if __name__ == "__main__":
    main()
