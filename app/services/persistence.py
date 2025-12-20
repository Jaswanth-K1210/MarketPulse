import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.services.database import get_db_connection
from app.models.article import Article

logger = logging.getLogger(__name__)

class PersistenceService:
    def __init__(self):
        pass

    # --- COMPANY MANAGEMENT ---
    def get_portfolio_stocks(self) -> List[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM companies WHERE is_portfolio = 1")
        rows = cursor.fetchall()
        conn.close()
        return [row['ticker'] for row in rows]

    def get_all_tracked_tickers(self) -> List[str]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM companies")
        rows = cursor.fetchall()
        conn.close()
        return [row['ticker'] for row in rows]

    # --- RELATIONSHIP CACHING ---
    def get_cached_relationships(self, ticker: str) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT target_ticker, relationship_type, criticality, confidence 
            FROM relationships 
            WHERE source_ticker = ?
        """, (ticker,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "related_company": row['target_ticker'],
            "type": row['relationship_type'],
            "criticality": row['criticality'],
            "confidence": row['confidence']
        } for row in rows]

    def save_discovered_relationships(self, source_ticker: str, relationships: List[Dict]):
        conn = get_db_connection()
        cursor = conn.cursor()
        for rel in relationships:
            cursor.execute("""
                INSERT OR REPLACE INTO relationships 
                (source_ticker, target_ticker, relationship_type, criticality, confidence, source_discovery, last_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                source_ticker, 
                rel['related_company'], 
                rel['type'], 
                rel['criticality'], 
                rel.get('confidence', 0.8),
                rel.get('source', 'dynamic_discovery'),
                datetime.now()
            ))
        conn.commit()
        conn.close()

    # --- ARTICLE PERSISTENCE ---
    def save_article(self, article: Article):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO articles 
            (id, title, url, source, content, published_at, priority, relevance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article.id, article.title, article.url, article.source, 
            article.content, article.published_at, article.priority, article.relevance
        ))
        conn.commit()
        conn.close()

    def get_recent_articles(self, limit: int = 10) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles ORDER BY published_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # --- ALERT & REASONING TRAIL ---
    def save_alert(self, alert_id: str, headline: str, severity: str, impact_pct: float, article_id: str, reasoning_trail: List[Dict]):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save Alert
        cursor.execute("""
            INSERT OR REPLACE INTO alerts (id, headline, severity, impact_pct, trigger_article_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (alert_id, headline, severity, impact_pct, article_id, datetime.now()))
        
        # Save Reasoning Trail (Impact Analysis)
        for step in reasoning_trail:
            cursor.execute("""
                INSERT INTO impact_analysis (alert_id, ticker, impact_level, reasoning, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (alert_id, step['ticker'], step['level'], step['reasoning'], step.get('confidence', 0.9)))
            
        conn.commit()
        conn.close()

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_alert_details(self, alert_id: str) -> Dict:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        alert = cursor.fetchone()
        if not alert:
            conn.close()
            return None
            
        cursor.execute("SELECT * FROM impact_analysis WHERE alert_id = ?", (alert_id,))
        trail = cursor.fetchall()
        conn.close()
        
        res = dict(alert)
        res['reasoning_trail'] = [dict(t) for t in trail]
        return res

persistence_service = PersistenceService()
