"""
Automated Alert Generation Service
Continuously processes news and generates alerts based on portfolio impact
Uses the sophisticated 7-Stage Pipeline for consistent logic.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
import uuid

# Use the centralized Pipeline logic
from app.services.pipeline import Pipeline
from app.models.article import Article

logger = logging.getLogger(__name__)

class AlertGenerator:
    def __init__(self):
        self.pipeline = Pipeline()

    def generate_alerts_from_news(self, news_articles: List[Dict], portfolio: List[Dict]) -> int:
        """
        Main entry point: Process news articles and generate alerts.
        Delegates to the Pipeline to ensure Cascade Inference and Relation Graph logic 
        is applied consistently across both background and manual triggers.

        Returns number of alerts created.
        """
        alerts_created = 0
        
        logger.info(f"⚡ AlertGenerator: Processing {len(news_articles)} articles via Pipeline...")

        for article_data in news_articles:
            try:
                # Convert dict to Article object required by Pipeline
                # Handle potentially missing fields gracefully
                article_obj = Article(
                    title=article_data.get('title', 'Unknown News'),
                    url=article_data.get('url', 'http://unknown.source'),
                    source=article_data.get('source', 'Unknown Source'),
                    published_at=datetime.now(), # Default
                    content=article_data.get('content') or article_data.get('description', '') or article_data.get('title', ''),
                    companies_mentioned=[] # Pipeline will extract this
                )
                
                # Execute Pipeline
                # This performs: Validation -> Relation Extraction -> Cascade Inference -> Impact Calc -> Persistence
                alert = self.pipeline.process_article(article_obj)

                if alert:
                    alerts_created += 1
                    logger.info(f"✅ Alert Created via Pipeline: {alert.id}")
            
            except Exception as e:
                logger.error(f"Error processing article '{article_data.get('title', 'Unknown')}': {e}")
                continue

        logger.info(f"✅ Alert Generation Complete. Total New Alerts: {alerts_created}")
        return alerts_created

# Global instance
alert_generator = AlertGenerator()
