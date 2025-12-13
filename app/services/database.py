"""
Database Service
JSON file-based storage for articles, alerts, relationships, and knowledge graphs
"""

import json
import logging
import os
from typing import List, Optional, Dict
from datetime import datetime
from app.config import (
    ARTICLES_DB, ALERTS_DB, RELATIONSHIPS_DB,
    PORTFOLIO_DB, KNOWLEDGE_GRAPHS_DB, DATA_DIR
)
from app.models.article import Article
from app.models.alert import Alert
from app.models.knowledge_graph import KnowledgeGraph

logger = logging.getLogger(__name__)


class Database:
    """JSON file-based database"""

    def __init__(self):
        """Initialize database"""
        self._ensure_files_exist()
        logger.info("Database initialized with JSON file storage")

    def _ensure_files_exist(self):
        """Ensure all database files exist"""
        for db_file in [ARTICLES_DB, ALERTS_DB, RELATIONSHIPS_DB, PORTFOLIO_DB, KNOWLEDGE_GRAPHS_DB]:
            if not os.path.exists(db_file):
                with open(db_file, 'w') as f:
                    json.dump([], f)
                logger.info(f"Created database file: {db_file}")

    def _read_file(self, filepath: str) -> List[Dict]:
        """Read JSON file"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {filepath}, returning empty list")
            return []
        except Exception as e:
            logger.error(f"Error reading {filepath}: {str(e)}")
            return []

    def _write_file(self, filepath: str, data: List[Dict]):
        """Write JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error writing {filepath}: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════
    # ARTICLE METHODS
    # ═══════════════════════════════════════════════════════════════════

    def save_article(self, article: Article) -> None:
        """Save article to database"""
        try:
            articles = self._read_file(ARTICLES_DB)

            # Check if article already exists (by URL)
            existing_urls = [a.get('url') for a in articles]
            if article.url in existing_urls:
                logger.info(f"Article already exists: {article.url}")
                return

            articles.append(article.to_dict())
            self._write_file(ARTICLES_DB, articles)
            logger.info(f"Saved article: {article.title}")
        except Exception as e:
            logger.error(f"Error saving article: {str(e)}")

    def get_article(self, article_id: str) -> Optional[Article]:
        """Get article by ID"""
        articles = self._read_file(ARTICLES_DB)
        for article_data in articles:
            if article_data.get('id') == article_id:
                return Article.from_dict(article_data)
        return None

    def get_all_articles(self, limit: int = 100) -> List[Article]:
        """Get all articles, sorted by most recent first"""
        articles = self._read_file(ARTICLES_DB)
        article_objects = [Article.from_dict(a) for a in articles]
        # Sort by published_at descending (most recent first)
        article_objects.sort(key=lambda x: x.published_at, reverse=True)
        return article_objects[:limit]

    def get_recent_articles(self, hours: int = 24) -> List[Article]:
        """Get articles from last N hours"""
        articles = self._read_file(ARTICLES_DB)
        cutoff = datetime.now().timestamp() - (hours * 3600)

        recent = []
        for article_data in articles:
            pub_time = datetime.fromisoformat(article_data.get('published_at'))
            if pub_time.timestamp() > cutoff:
                recent.append(Article.from_dict(article_data))

        return recent

    # ═══════════════════════════════════════════════════════════════════
    # ALERT METHODS
    # ═══════════════════════════════════════════════════════════════════

    def save_alert(self, alert: Alert) -> None:
        """Save alert to database"""
        try:
            alerts = self._read_file(ALERTS_DB)
            alerts.append(alert.to_dict())
            self._write_file(ALERTS_DB, alerts)
            logger.info(f"Saved alert: {alert.id} (severity: {alert.severity})")
        except Exception as e:
            logger.error(f"Error saving alert: {str(e)}")

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        alerts = self._read_file(ALERTS_DB)
        for alert_data in alerts:
            if alert_data.get('id') == alert_id:
                return Alert.from_dict(alert_data)
        return None

    def get_all_alerts(self, limit: int = 50) -> List[Alert]:
        """Get all alerts (most recent first)"""
        alerts = self._read_file(ALERTS_DB)
        # Sort by created_at descending
        alerts_sorted = sorted(
            alerts,
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
        return [Alert.from_dict(a) for a in alerts_sorted[:limit]]

    def get_alerts_by_severity(self, severity: str, limit: int = 50) -> List[Alert]:
        """Get alerts by severity level"""
        alerts = self._read_file(ALERTS_DB)
        filtered = [a for a in alerts if a.get('severity') == severity]
        filtered_sorted = sorted(filtered, key=lambda x: x.get('created_at', ''), reverse=True)
        return [Alert.from_dict(a) for a in filtered_sorted[:limit]]

    def get_alerts_for_company(self, company: str) -> List[Alert]:
        """Get alerts affecting a specific company"""
        alerts = self._read_file(ALERTS_DB)
        relevant = []

        for alert_data in alerts:
            # Check if company is in affected_holdings
            holdings = alert_data.get('affected_holdings', [])
            for holding in holdings:
                if holding.get('company') == company or holding.get('ticker') == company:
                    relevant.append(Alert.from_dict(alert_data))
                    break

        return relevant

    # ═══════════════════════════════════════════════════════════════════
    # RELATIONSHIP METHODS
    # ═══════════════════════════════════════════════════════════════════

    def save_relationship(self, relationship: Dict) -> None:
        """Save company relationship"""
        try:
            relationships = self._read_file(RELATIONSHIPS_DB)
            relationships.append({
                **relationship,
                'created_at': datetime.now().isoformat()
            })
            self._write_file(RELATIONSHIPS_DB, relationships)
            logger.info(f"Saved relationship: {relationship.get('from_company')} -> {relationship.get('to_company')}")
        except Exception as e:
            logger.error(f"Error saving relationship: {str(e)}")

    def get_relationships_for_company(self, company: str) -> List[Dict]:
        """Get all relationships involving a company"""
        relationships = self._read_file(RELATIONSHIPS_DB)
        return [
            r for r in relationships
            if r.get('from_company') == company or r.get('to_company') == company
        ]

    # ═══════════════════════════════════════════════════════════════════
    # KNOWLEDGE GRAPH METHODS
    # ═══════════════════════════════════════════════════════════════════

    def save_knowledge_graph(self, graph: KnowledgeGraph) -> None:
        """Save knowledge graph"""
        try:
            graphs = self._read_file(KNOWLEDGE_GRAPHS_DB)
            graphs.append(graph.to_dict())
            self._write_file(KNOWLEDGE_GRAPHS_DB, graphs)
            logger.info(f"Saved knowledge graph for alert: {graph.alert_id}")
        except Exception as e:
            logger.error(f"Error saving knowledge graph: {str(e)}")

    def get_knowledge_graph(self, alert_id: str) -> Optional[KnowledgeGraph]:
        """Get knowledge graph for alert"""
        graphs = self._read_file(KNOWLEDGE_GRAPHS_DB)
        for graph_data in graphs:
            if graph_data.get('alert_id') == alert_id:
                return KnowledgeGraph.from_dict(graph_data)
        return None

    # ═══════════════════════════════════════════════════════════════════
    # PORTFOLIO METHODS
    # ═══════════════════════════════════════════════════════════════════

    def save_portfolio(self, portfolio_data: Dict) -> None:
        """Save portfolio data"""
        try:
            self._write_file(PORTFOLIO_DB, [portfolio_data])
            logger.info(f"Saved portfolio for user: {portfolio_data.get('user_name')}")
        except Exception as e:
            logger.error(f"Error saving portfolio: {str(e)}")

    def get_portfolio(self) -> Optional[Dict]:
        """Get portfolio data"""
        portfolios = self._read_file(PORTFOLIO_DB)
        return portfolios[0] if portfolios else None

    # ═══════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════

    def clear_all(self):
        """Clear all database files (for testing)"""
        for db_file in [ARTICLES_DB, ALERTS_DB, RELATIONSHIPS_DB, KNOWLEDGE_GRAPHS_DB]:
            self._write_file(db_file, [])
        logger.warning("Cleared all database files")

    def get_stats(self) -> Dict:
        """Get database statistics"""
        return {
            "articles_count": len(self._read_file(ARTICLES_DB)),
            "alerts_count": len(self._read_file(ALERTS_DB)),
            "relationships_count": len(self._read_file(RELATIONSHIPS_DB)),
            "graphs_count": len(self._read_file(KNOWLEDGE_GRAPHS_DB)),
            "has_portfolio": bool(self.get_portfolio())
        }


# Create singleton instance
database = Database()
