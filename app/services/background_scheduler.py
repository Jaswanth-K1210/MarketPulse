"""
Background Scheduler for Continuous Processing
Runs periodic tasks: news ingestion, alert generation, relationship updates
"""
import logging
import threading
import time
from datetime import datetime
from typing import Callable

logger = logging.getLogger(__name__)

class BackgroundScheduler:
    def __init__(self):
        self.tasks = []
        self.running = False
        self.thread = None

    def add_task(self, name: str, func: Callable, interval_seconds: int):
        """Register a task to run periodically."""
        self.tasks.append({
            'name': name,
            'func': func,
            'interval': interval_seconds,
            'last_run': 0
        })
        logger.info(f"📅 Scheduled task '{name}' to run every {interval_seconds}s")

    def start(self):
        """Start background processing."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 Background scheduler started")

    def stop(self):
        """Stop background processing."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Background scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            current_time = time.time()

            for task in self.tasks:
                # Check if task is due
                time_since_last_run = current_time - task['last_run']
                if time_since_last_run >= task['interval']:
                    try:
                        logger.info(f"⏰ Running task: {task['name']}")
                        task['func']()
                        task['last_run'] = current_time
                    except Exception as e:
                        logger.error(f"❌ Task '{task['name']}' failed: {e}")

            # Sleep for 10 seconds before next check
            time.sleep(10)

# Global scheduler instance
scheduler = BackgroundScheduler()

def start_background_tasks():
    """Initialize and start all background tasks."""
    from app.services.alert_generator import alert_generator
    from app.services.news_aggregator import NewsIngestionLayer
    from app.services.database import get_db_connection

    def news_to_alerts_job():
        """Fetch news and generate alerts."""
        try:
            # Get portfolio
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker, company_name FROM holdings")
            portfolio = [dict(row) for row in cursor.fetchall()]
            conn.close()

            if not portfolio:
                logger.warning("No portfolio found, skipping alert generation")
                return

            # Fetch news
            news_layer = NewsIngestionLayer()
            tickers = [p['ticker'] for p in portfolio]
            query = " OR ".join(tickers)

            articles = []
            articles.extend(news_layer.fetch_news_api(query) or [])
            articles.extend(news_layer.fetch_finnhub(query) or [])
            articles.extend(news_layer.fetch_gnews(query) or [])

            logger.info(f"📰 Fetched {len(articles)} news articles")

            # Generate alerts
            alerts_count = alert_generator.generate_alerts_from_news(articles[:20], portfolio)
            logger.info(f"✅ Generated {alerts_count} alerts")

        except Exception as e:
            logger.error(f"News-to-alerts job failed: {e}")

    def relationship_update_job():
        """Update relationships for portfolio companies."""
        try:
            from app.agents.nodes import agent_3b_discovery

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ticker FROM holdings")
            tickers = [row['ticker'] for row in cursor.fetchall()]
            conn.close()

            logger.info(f"🔄 Updating relationships for {len(tickers)} companies...")

            for ticker in tickers:
                try:
                    state = {"portfolio": tickers}
                    agent_3b_discovery(state)
                except Exception as e:
                    logger.error(f"Relationship update failed for {ticker}: {e}")

            logger.info("✅ Relationship updates complete")

        except Exception as e:
            logger.error(f"Relationship update job failed: {e}")

    # Schedule tasks
    scheduler.add_task("News-to-Alerts", news_to_alerts_job, interval_seconds=300)  # Every 5 min
    scheduler.add_task("Relationship-Updates", relationship_update_job, interval_seconds=3600)  # Every hour

    # Start scheduler
    scheduler.start()
